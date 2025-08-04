"""
MCP Protocol Version Negotiation and Compliance.

This module handles MCP protocol version negotiation and ensures compliance
with MCP-SPEC-101 requirements for proper protocol handshake.
"""

import logging
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from packaging import version

# Import CloudWatch for audit logging
try:
    import boto3

    CLOUDWATCH_AVAILABLE = True
except ImportError:
    CLOUDWATCH_AVAILABLE = False

logger = logging.getLogger(__name__)


class ProtocolVersion(Enum):
    """Supported MCP Protocol Versions."""

    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"


@dataclass
class ProtocolCapabilities:
    """MCP Protocol Capabilities."""

    # Core capabilities
    supports_streaming: bool = False
    supports_binary_content: bool = False
    supports_progress_reporting: bool = True
    supports_cancellation: bool = False

    # Tool capabilities
    supports_tool_schemas: bool = True
    supports_tool_validation: bool = True
    supports_tool_metadata: bool = True

    # Resource capabilities
    supports_resources: bool = True
    supports_resource_templates: bool = False
    supports_resource_subscriptions: bool = False

    # Error handling capabilities
    supports_structured_errors: bool = True
    supports_error_context: bool = True
    supports_troubleshooting_info: bool = True

    # CloudWAN specific capabilities
    supports_multi_region_ops: bool = True
    supports_aws_error_mapping: bool = True
    supports_network_analysis: bool = True


@dataclass
class ProtocolConfiguration:
    """MCP Protocol Configuration."""

    version: str
    capabilities: ProtocolCapabilities
    server_name: str
    server_version: str
    supported_content_types: List[str]
    max_request_size: int = 1024 * 1024  # 1MB default
    request_timeout: int = 300  # 5 minutes default
    heartbeat_interval: int = 30  # 30 seconds default


@dataclass
class ProtocolAuditEvent:
    """Security audit event for protocol operations."""

    timestamp: str
    event_type: (
        str  # NEGOTIATION_START, NEGOTIATION_COMPLETE, VERSION_DOWNGRADE, SECURITY_VIOLATION
    )
    client_versions: List[str]
    negotiated_version: Optional[str]
    security_level: str
    client_ip: Optional[str]
    user_agent: Optional[str]
    result: str  # SUCCESS, FAILED, SECURITY_DENIED
    error_message: Optional[str] = None
    compliance_issues: List[str] = None

    def __post_init__(self):
        if self.compliance_issues is None:
            self.compliance_issues = []


class SecurityAuditLogger:
    """PCI-DSS compliant audit logger for MCP protocol operations."""

    def __init__(
        self,
        enable_cloudwatch: bool = True,
        log_group_name: str = "/aws/mcp/security-audit",
    ):
        self.enable_cloudwatch = enable_cloudwatch and CLOUDWATCH_AVAILABLE
        self.log_group_name = log_group_name
        self._cloudwatch_client = None
        self._audit_buffer: List[ProtocolAuditEvent] = []

        # PCI-DSS requirement: Secure audit log storage
        if self.enable_cloudwatch:
            try:
                self._cloudwatch_client = boto3.client("logs")
                self._ensure_log_group_exists()
            except Exception as e:
                logger.warning(f"CloudWatch audit logging unavailable: {e}")
                self.enable_cloudwatch = False

    def _ensure_log_group_exists(self) -> None:
        """Ensure CloudWatch log group exists for audit logs."""
        if not self._cloudwatch_client:
            return

        try:
            self._cloudwatch_client.create_log_group(
                logGroupName=self.log_group_name,
                kmsKeyId="alias/aws/logs",  # KMS encryption at rest
            )

            # Set retention policy (PCI-DSS requires minimum 1 year)
            self._cloudwatch_client.put_retention_policy(
                logGroupName=self.log_group_name, retentionInDays=365
            )

        except self._cloudwatch_client.exceptions.ResourceAlreadyExistsException:
            pass  # Log group already exists
        except Exception as e:
            logger.error(f"Failed to create audit log group: {e}")

    def log_protocol_event(self, event: ProtocolAuditEvent) -> None:
        """
        Log protocol security event with PCI-DSS compliance.

        PCI-DSS 10.2 requirements:
        - All individual user accesses to cardholder data
        - All actions taken by root or administrative privilege
        - Access to all audit trails
        - Invalid logical access attempts
        - Use of identification and authentication mechanisms
        """
        # Add to buffer for batch processing
        self._audit_buffer.append(event)

        # Create structured log message
        audit_message = {
            "timestamp": event.timestamp,
            "event_type": event.event_type,
            "protocol_negotiation": {
                "client_versions": event.client_versions,
                "negotiated_version": event.negotiated_version,
                "downgrade_detected": self._is_version_downgrade(
                    event.client_versions, event.negotiated_version
                ),
            },
            "security_context": {
                "level": event.security_level,
                "client_ip": event.client_ip,
                "user_agent": event.user_agent,
            },
            "result": event.result,
            "error_message": event.error_message,
            "compliance_issues": event.compliance_issues,
            "pci_dss_category": self._get_pci_dss_category(event),
            "session_id": f"mcp-{hash(str(event.timestamp))}",
        }

        # Log to local logger (always)
        logger.info(f"PROTOCOL_AUDIT: {json.dumps(audit_message, separators=(',', ':'))}")

        # Log to CloudWatch if enabled
        if self.enable_cloudwatch:
            self._send_to_cloudwatch(audit_message)

        # Keep buffer size manageable
        if len(self._audit_buffer) > 1000:
            self._audit_buffer = self._audit_buffer[-500:]  # Keep last 500 events

    def _is_version_downgrade(
        self, client_versions: List[str], negotiated_version: Optional[str]
    ) -> bool:
        """Detect if protocol version was downgraded from client preferences."""
        if not negotiated_version or not client_versions:
            return False

        try:
            # Parse versions and check if negotiated is lower than highest client version
            client_version_objects = [version.parse(v) for v in client_versions]
            negotiated_version_obj = version.parse(negotiated_version)
            highest_client_version = max(client_version_objects)

            return negotiated_version_obj < highest_client_version
        except Exception:
            return False

    def _get_pci_dss_category(self, event: ProtocolAuditEvent) -> str:
        """Categorize event according to PCI-DSS requirements."""
        if event.event_type == "SECURITY_VIOLATION":
            return "10.2.4-invalid-access-attempt"
        elif event.event_type == "VERSION_DOWNGRADE":
            return "10.2.5-identification-authentication"
        elif event.result == "FAILED":
            return "10.2.4-invalid-access-attempt"
        else:
            return "10.2.5-identification-authentication"

    def _send_to_cloudwatch(self, audit_message: Dict[str, Any]) -> None:
        """Send audit message to CloudWatch Logs."""
        if not self._cloudwatch_client:
            return

        try:
            # Create log stream if needed
            stream_name = f"protocol-audit-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"

            try:
                self._cloudwatch_client.create_log_stream(
                    logGroupName=self.log_group_name, logStreamName=stream_name
                )
            except self._cloudwatch_client.exceptions.ResourceAlreadyExistsException:
                pass

            # Send log event
            self._cloudwatch_client.put_log_events(
                logGroupName=self.log_group_name,
                logStreamName=stream_name,
                logEvents=[
                    {
                        "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
                        "message": json.dumps(audit_message, separators=(",", ":")),
                    }
                ],
            )

        except Exception as e:
            logger.error(f"Failed to send audit log to CloudWatch: {e}")

    def get_audit_summary(self) -> Dict[str, Any]:
        """Get summary of recent audit events."""
        if not self._audit_buffer:
            return {"total_events": 0, "recent_events": []}

        # Count events by type
        event_counts = {}
        security_violations = 0
        downgrades = 0

        for event in self._audit_buffer[-100:]:  # Last 100 events
            event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1
            if event.event_type == "SECURITY_VIOLATION":
                security_violations += 1
            elif event.event_type == "VERSION_DOWNGRADE":
                downgrades += 1

        return {
            "total_events": len(self._audit_buffer),
            "event_type_counts": event_counts,
            "security_violations": security_violations,
            "version_downgrades": downgrades,
            "recent_events": [
                {
                    "timestamp": event.timestamp,
                    "type": event.event_type,
                    "result": event.result,
                }
                for event in self._audit_buffer[-10:]  # Last 10 events
            ],
        }


class ProtocolNegotiator:
    """Handles MCP protocol version negotiation and capability exchange."""

    # Supported versions in preference order (highest first)
    SUPPORTED_VERSIONS = [
        ProtocolVersion.V2_0.value,
        ProtocolVersion.V1_1.value,
        ProtocolVersion.V1_0.value,
    ]

    # Minimum required version
    MINIMUM_VERSION = ProtocolVersion.V1_0.value

    def __init__(self, server_name: str, server_version: str, enable_audit_logging: bool = True):
        self.server_name = server_name
        self.server_version = server_version
        self.negotiated_config: Optional[ProtocolConfiguration] = None

        # Initialize security audit logger
        self.audit_logger = SecurityAuditLogger() if enable_audit_logging else None

    def negotiate_protocol(
        self,
        client_supported_versions: List[str],
        client_capabilities: Optional[Dict[str, Any]] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        security_level: str = "development",
    ) -> ProtocolConfiguration:
        """
        Negotiate protocol version and capabilities with client.

        Args:
            client_supported_versions: Versions supported by client
            client_capabilities: Capabilities requested by client
            client_ip: Client IP address for audit logging
            user_agent: Client user agent for audit logging
            security_level: Security level for audit logging

        Returns:
            Negotiated protocol configuration

        Raises:
            ValueError: If no compatible version found
        """
        # Log negotiation start
        if self.audit_logger:
            self.audit_logger.log_protocol_event(
                ProtocolAuditEvent(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    event_type="NEGOTIATION_START",
                    client_versions=client_supported_versions,
                    negotiated_version=None,
                    security_level=security_level,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    result="IN_PROGRESS",
                )
            )

        # Find highest mutually supported version
        negotiated_version = self._find_compatible_version(client_supported_versions)

        if not negotiated_version:
            # Log negotiation failure
            if self.audit_logger:
                self.audit_logger.log_protocol_event(
                    ProtocolAuditEvent(
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        event_type="NEGOTIATION_COMPLETE",
                        client_versions=client_supported_versions,
                        negotiated_version=None,
                        security_level=security_level,
                        client_ip=client_ip,
                        user_agent=user_agent,
                        result="FAILED",
                        error_message="No compatible protocol version found",
                        compliance_issues=["INCOMPATIBLE_PROTOCOL_VERSIONS"],
                    )
                )

            raise ValueError(
                f"No compatible protocol version found. "
                f"Server supports: {self.SUPPORTED_VERSIONS}, "
                f"Client supports: {client_supported_versions}"
            )

        # Detect version downgrade for security audit
        is_downgrade = self._is_version_downgrade(client_supported_versions, negotiated_version)
        if is_downgrade and self.audit_logger:
            self.audit_logger.log_protocol_event(
                ProtocolAuditEvent(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    event_type="VERSION_DOWNGRADE",
                    client_versions=client_supported_versions,
                    negotiated_version=negotiated_version,
                    security_level=security_level,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    result="WARNING",
                    compliance_issues=["PROTOCOL_VERSION_DOWNGRADE"],
                )
            )

        # Build capabilities based on negotiated version
        capabilities = self._build_capabilities(negotiated_version, client_capabilities)

        # Create configuration
        config = ProtocolConfiguration(
            version=negotiated_version,
            capabilities=capabilities,
            server_name=self.server_name,
            server_version=self.server_version,
            supported_content_types=self._get_supported_content_types(negotiated_version),
        )

        self.negotiated_config = config

        # Log successful negotiation
        if self.audit_logger:
            self.audit_logger.log_protocol_event(
                ProtocolAuditEvent(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    event_type="NEGOTIATION_COMPLETE",
                    client_versions=client_supported_versions,
                    negotiated_version=negotiated_version,
                    security_level=security_level,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    result="SUCCESS",
                )
            )

        logger.info(
            f"Protocol negotiated: version={negotiated_version}, "
            f"capabilities={len(self._capability_summary(capabilities))} features"
        )

        return config

    def _is_version_downgrade(self, client_versions: List[str], negotiated_version: str) -> bool:
        """Check if negotiated version is a downgrade from client preferences."""
        try:
            client_version_objects = [version.parse(v) for v in client_versions]
            negotiated_version_obj = version.parse(negotiated_version)
            highest_client_version = max(client_version_objects)

            return negotiated_version_obj < highest_client_version
        except Exception:
            return False

    def _find_compatible_version(self, client_versions: List[str]) -> Optional[str]:
        """Find highest mutually supported version."""
        # Parse and sort client versions
        try:
            client_version_objects = [version.parse(v) for v in client_versions]
            server_version_objects = [version.parse(v) for v in self.SUPPORTED_VERSIONS]
        except Exception as e:
            logger.warning(f"Version parsing failed: {e}")
            # Fallback to string comparison
            return self._find_compatible_version_fallback(client_versions)

        # Find intersection, preferring highest version
        compatible_versions = []
        for server_ver in server_version_objects:
            for client_ver in client_version_objects:
                if server_ver == client_ver:
                    compatible_versions.append(str(server_ver))

        if compatible_versions:
            # Sort by version and return highest
            compatible_versions.sort(key=version.parse, reverse=True)
            return compatible_versions[0]

        return None

    def _find_compatible_version_fallback(self, client_versions: List[str]) -> Optional[str]:
        """Fallback version negotiation using string comparison."""
        for server_version in self.SUPPORTED_VERSIONS:
            if server_version in client_versions:
                return server_version
        return None

    def _build_capabilities(
        self, protocol_version: str, client_capabilities: Optional[Dict[str, Any]]
    ) -> ProtocolCapabilities:
        """Build server capabilities based on version and client requirements."""
        capabilities = ProtocolCapabilities()

        # Version-specific capabilities
        if version.parse(protocol_version) >= version.parse("1.1"):
            capabilities.supports_progress_reporting = True
            capabilities.supports_tool_metadata = True

        if version.parse(protocol_version) >= version.parse("2.0"):
            capabilities.supports_streaming = True
            capabilities.supports_binary_content = True
            capabilities.supports_cancellation = True
            capabilities.supports_resource_subscriptions = True

        # Client capability negotiation
        if client_capabilities:
            # Only enable capabilities supported by both client and server
            if not client_capabilities.get("supports_streaming", True):
                capabilities.supports_streaming = False

            if not client_capabilities.get("supports_progress_reporting", True):
                capabilities.supports_progress_reporting = False

            if not client_capabilities.get("supports_structured_errors", True):
                capabilities.supports_structured_errors = False

        return capabilities

    def _get_supported_content_types(self, protocol_version: str) -> List[str]:
        """Get supported content types for protocol version."""
        content_types = ["text/plain", "application/json"]

        if version.parse(protocol_version) >= version.parse("2.0"):
            content_types.extend(["application/octet-stream", "image/png", "image/jpeg"])

        return content_types

    def _capability_summary(self, capabilities: ProtocolCapabilities) -> Dict[str, bool]:
        """Get summary of enabled capabilities."""
        return {
            attr: getattr(capabilities, attr)
            for attr in dir(capabilities)
            if not attr.startswith("_") and isinstance(getattr(capabilities, attr), bool)
        }

    def get_protocol_info(self) -> Dict[str, Any]:
        """Get current protocol information."""
        if not self.negotiated_config:
            return {
                "status": "not_negotiated",
                "supported_versions": self.SUPPORTED_VERSIONS,
                "minimum_version": self.MINIMUM_VERSION,
            }

        config = self.negotiated_config
        return {
            "status": "negotiated",
            "version": config.version,
            "server_name": config.server_name,
            "server_version": config.server_version,
            "capabilities": self._capability_summary(config.capabilities),
            "supported_content_types": config.supported_content_types,
            "limits": {
                "max_request_size": config.max_request_size,
                "request_timeout": config.request_timeout,
                "heartbeat_interval": config.heartbeat_interval,
            },
        }

    def validate_request(self, request: Dict[str, Any]) -> bool:
        """
        Validate request against negotiated protocol.

        Args:
            request: MCP request to validate

        Returns:
            True if valid, False otherwise
        """
        if not self.negotiated_config:
            logger.warning("Protocol not negotiated, cannot validate request")
            return False

        # Basic validation
        required_fields = ["jsonrpc", "method"]
        for field in required_fields:
            if field not in request:
                logger.warning(f"Request missing required field: {field}")
                return False

        # Version validation
        if request.get("jsonrpc") != "2.0":
            logger.warning(f"Invalid JSON-RPC version: {request.get('jsonrpc')}")
            return False

        # Size validation
        request_size = len(str(request).encode("utf-8"))
        if request_size > self.negotiated_config.max_request_size:
            logger.warning(
                f"Request size {request_size} exceeds limit {self.negotiated_config.max_request_size}"
            )
            return False

        return True

    def is_feature_supported(self, feature: str) -> bool:
        """Check if a specific feature is supported in current protocol."""
        if not self.negotiated_config:
            return False

        return getattr(self.negotiated_config.capabilities, f"supports_{feature}", False)


class ProtocolComplianceChecker:
    """Ensures MCP protocol compliance throughout the session."""

    def __init__(self, negotiator: ProtocolNegotiator):
        self.negotiator = negotiator
        self.violations: List[Dict[str, Any]] = []

    def check_response_compliance(self, response: Dict[str, Any]) -> bool:
        """Check if response complies with negotiated protocol."""
        if not self.negotiator.negotiated_config:
            self.violations.append(
                {
                    "type": "protocol_not_negotiated",
                    "message": "Response generated without protocol negotiation",
                    "response_id": response.get("id"),
                }
            )
            return False

        # Check required fields
        if "jsonrpc" not in response:
            self.violations.append(
                {
                    "type": "missing_jsonrpc",
                    "message": "Response missing 'jsonrpc' field",
                    "response_id": response.get("id"),
                }
            )
            return False

        if response["jsonrpc"] != "2.0":
            self.violations.append(
                {
                    "type": "invalid_jsonrpc_version",
                    "message": f"Invalid JSON-RPC version: {response['jsonrpc']}",
                    "response_id": response.get("id"),
                }
            )
            return False

        # Check for either result or error (but not both)
        has_result = "result" in response
        has_error = "error" in response

        if has_result and has_error:
            self.violations.append(
                {
                    "type": "result_and_error",
                    "message": "Response contains both 'result' and 'error'",
                    "response_id": response.get("id"),
                }
            )
            return False

        if not has_result and not has_error:
            self.violations.append(
                {
                    "type": "no_result_or_error",
                    "message": "Response missing both 'result' and 'error'",
                    "response_id": response.get("id"),
                }
            )
            return False

        # Check error structure if present
        if has_error:
            error = response["error"]
            if not isinstance(error, dict):
                self.violations.append(
                    {
                        "type": "invalid_error_format",
                        "message": "Error field must be an object",
                        "response_id": response.get("id"),
                    }
                )
                return False

            if "code" not in error or "message" not in error:
                self.violations.append(
                    {
                        "type": "incomplete_error",
                        "message": "Error missing required 'code' or 'message' field",
                        "response_id": response.get("id"),
                    }
                )
                return False

        return True

    def get_compliance_report(self) -> Dict[str, Any]:
        """Get compliance violation report."""
        return {
            "total_violations": len(self.violations),
            "violation_types": list(set(v["type"] for v in self.violations)),
            "violations": self.violations[-10:],  # Last 10 violations
            "is_compliant": len(self.violations) == 0,
        }

    def clear_violations(self) -> None:
        """Clear recorded violations."""
        self.violations.clear()


# Global protocol negotiator (initialized by server)
_protocol_negotiator: Optional[ProtocolNegotiator] = None
_compliance_checker: Optional[ProtocolComplianceChecker] = None


def initialize_protocol(server_name: str, server_version: str) -> ProtocolNegotiator:
    """Initialize global protocol negotiator."""
    global _protocol_negotiator, _compliance_checker

    _protocol_negotiator = ProtocolNegotiator(server_name, server_version)
    _compliance_checker = ProtocolComplianceChecker(_protocol_negotiator)

    logger.info(f"Protocol negotiator initialized for {server_name} v{server_version}")
    return _protocol_negotiator


def get_protocol_negotiator() -> Optional[ProtocolNegotiator]:
    """Get global protocol negotiator."""
    return _protocol_negotiator


def get_compliance_checker() -> Optional[ProtocolComplianceChecker]:
    """Get global compliance checker."""
    return _compliance_checker


def negotiate_protocol_version(
    client_versions: List[str], client_capabilities: Optional[Dict[str, Any]] = None
) -> ProtocolConfiguration:
    """Negotiate protocol version with client."""
    if not _protocol_negotiator:
        raise RuntimeError("Protocol negotiator not initialized")

    return _protocol_negotiator.negotiate_protocol(client_versions, client_capabilities)


def is_protocol_feature_supported(feature: str) -> bool:
    """Check if protocol feature is supported."""
    if not _protocol_negotiator:
        return False

    return _protocol_negotiator.is_feature_supported(feature)


def validate_protocol_compliance(response: Dict[str, Any]) -> bool:
    """Validate response for protocol compliance."""
    if not _compliance_checker:
        return True  # No checker available, assume compliant

    return _compliance_checker.check_response_compliance(response)


def get_protocol_info() -> Dict[str, Any]:
    """Get current protocol information."""
    if not _protocol_negotiator:
        return {"status": "not_initialized"}

    return _protocol_negotiator.get_protocol_info()
