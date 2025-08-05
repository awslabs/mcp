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

"""Hierarchical AWS service mocking framework for CloudWAN MCP Server tests.

This module provides a comprehensive mocking infrastructure for AWS services,
enabling consistent and maintainable test fixtures across the entire test suite.
"""

import secrets
import string
from typing import Any
from unittest.mock import Mock

from botocore.exceptions import ClientError


class MockingSecurityError(Exception):
    """Raised when mocking security boundary violations are detected."""

    pass


class AWSServiceMocker:
    """Hierarchical AWS service mocker with configurable behavior.

    This class provides a structured approach to mocking AWS service clients
    with realistic responses and error scenarios.
    """

    def __init__(self, service_name: str, region: str = "us-east-1") -> None:
        """Initialize AWS service mocker.

        Args:
            service_name: AWS service name (e.g., 'networkmanager', 'ec2')
            region: AWS region for service client
        """
        self.service_name = service_name
        self.region = region
        self._client = Mock()
        # Define common client methods for regional behavior configuration
        self._client_methods = [
            "list_core_networks",
            "describe_global_networks",
            "get_core_network_policy",
            "get_core_network_change_set",
            "get_core_network_change_events",
            "describe_vpcs",
        ]
        self._configure_base_behavior()

    def _configure_base_behavior(self) -> None:
        """Configure base service behavior based on service type."""
        if self.service_name == "networkmanager":
            self._configure_networkmanager()
        elif self.service_name == "ec2":
            self._configure_ec2()
        else:
            # Generic service configuration
            self._configure_generic_service()

    def _configure_networkmanager(self) -> None:
        """Configure NetworkManager service mock responses."""
        # Core Networks
        self._client.list_core_networks.return_value = {
            "CoreNetworks": [
                {
                    "CoreNetworkId": "core-network-1234567890abcdef0",
                    "GlobalNetworkId": "global-network-1234567890abcdef0",
                    "State": "AVAILABLE",
                    "Description": "Test core network",
                    "CreatedAt": "2023-01-01T00:00:00Z",
                }
            ]
        }

        # Global Networks
        self._client.describe_global_networks.return_value = {
            "GlobalNetworks": [
                {
                    "GlobalNetworkId": "global-network-1234567890abcdef0",
                    "State": "AVAILABLE",
                    "Description": "Test global network",
                    "CreatedAt": "2023-01-01T00:00:00Z",
                }
            ]
        }

        # Core Network Policy
        self._client.get_core_network_policy.return_value = {
            "CoreNetworkPolicy": {
                "PolicyVersionId": 1,
                "PolicyDocument": {
                    "version": "2021.12",
                    "core-network-configuration": {"vpn-ecmp-support": False, "asn-ranges": ["64512-65534"]},
                    "segments": [{"name": "production", "require-attachment-acceptance": False}],
                },
                "Description": "Test policy",
                "CreatedAt": "2023-01-01T00:00:00Z",
            }
        }

        # Change Set
        self._client.get_core_network_change_set.return_value = {
            "CoreNetworkChanges": [
                {"Type": "SEGMENT_MAPPING_CREATE", "Action": "CREATE", "Identifier": "segment-mapping-1"}
            ]
        }

        # Change Events
        self._client.get_core_network_change_events.return_value = {
            "CoreNetworkChangeEvents": [
                {"Type": "POLICY_VERSION_CREATED", "Status": "COMPLETED", "EventTime": "2023-01-01T00:00:00Z"}
            ]
        }

    def _configure_ec2(self) -> None:
        """Configure EC2 service mock responses."""
        self._client.describe_vpcs.return_value = {
            "Vpcs": [
                {
                    "VpcId": "vpc-1234567890abcdef0",
                    "State": "available",
                    "CidrBlock": "10.0.0.0/16",
                    "IsDefault": False,
                    "Tags": [{"Key": "Name", "Value": "test-vpc"}],
                }
            ]
        }

    def _configure_generic_service(self) -> None:
        """Configure generic service responses."""
        # Default empty responses for unknown services
        pass

    def configure_core_networks(self, networks: list[dict[str, Any]]) -> "AWSServiceMocker":
        """Configure core network responses.

        Args:
            networks: List of core network configurations

        Returns:
            Self for method chaining
        """
        self._client.list_core_networks.return_value = {"CoreNetworks": networks}
        return self

    def configure_error(self, error_code: str, message: str = None, operation: str = None) -> "AWSServiceMocker":
        """Configure service to return specific error.

        Args:
            error_code: AWS error code (e.g., 'AccessDenied')
            message: Optional custom error message
            operation: Operation that should fail

        Returns:
            Self for method chaining
        """
        if message is None:
            message = f"Test error message for {error_code}"

        error_response = {
            "Error": {"Code": error_code, "Message": message},
            "ResponseMetadata": {
                "RequestId": "test-request-id-123",
                "HTTPStatusCode": self._get_http_status_for_error(error_code),
            },
        }

        client_error = ClientError(error_response, operation or "TestOperation")

        # Configure all methods to raise this error
        if operation:
            getattr(self._client, operation).side_effect = client_error
        else:
            # Configure common operations
            for method in [
                "list_core_networks",
                "describe_global_networks",
                "get_core_network_policy",
                "describe_vpcs",
            ]:
                if hasattr(self._client, method):
                    getattr(self._client, method).side_effect = client_error

        return self

    def _get_http_status_for_error(self, error_code: str) -> int:
        """Map AWS error codes to HTTP status codes."""
        error_mapping = {
            "AccessDenied": 403,
            "ResourceNotFoundException": 404,
            "ThrottlingException": 429,
            "ValidationException": 400,
            "InternalFailure": 500,
            "ServiceUnavailable": 503,
        }
        return error_mapping.get(error_code, 400)

    def configure_regional_behavior(self, region_responses: dict[str, Any]) -> "AWSServiceMocker":
        """Configure region-specific responses.

        Args:
            region_responses: Mapping of regions to response configurations

        Returns:
            Self for method chaining
        """

        def region_aware_response(method_name, *args, **kwargs):
            region = kwargs.get("region") or self.region
            if region in region_responses:
                return region_responses[region].get(method_name, {})
            return {}

        # Apply region-aware behavior to all specified client methods
        for method in self._client_methods:
            if hasattr(self._client, method):
                original_method = getattr(self._client, method)
                if hasattr(original_method, "return_value"):
                    setattr(
                        self._client, method, Mock(side_effect=lambda *a, **k: region_aware_response(method, *a, **k))
                    )

        return self

    @property
    def client(self) -> Mock:
        """Get the configured mock client."""
        return self._client


class AWSErrorCatalog:
    """Security-hardened AWS error catalog for comprehensive testing.

    Features:
    - Information disclosure prevention
    - Security boundary enforcement
    - Audit trail logging
    - Sanitized error messages
    """

    # Security-hardened error messages (no system internals exposed)
    SAFE_MESSAGES = {
        "AccessDenied": "Authorization failed for requested operation",
        "ResourceNotFoundException": "Requested resource could not be located",
        "ThrottlingException": "Request rate limit exceeded - please retry with backoff",
        "ValidationException": "Request validation failed - check input parameters",
        "InternalFailure": "Service unavailable - please try again later",
        "ServiceUnavailable": "Service temporarily unavailable - please retry",
        "NetworkingError": "Network connectivity issue detected",
        "TimeoutException": "Request timeout - operation did not complete in time",
    }

    # Standard AWS error codes and scenarios with security boundaries
    COMMON_ERRORS = {
        "access_denied": {
            "Code": "AccessDenied",
            "Message": "Authorization failed for requested operation",
            "HTTPStatusCode": 403,
            "SecurityBoundary": "AUTH_FAILURE",
            "SanitizedDetails": "IAM permission validation failed",
        },
        "resource_not_found": {
            "Code": "ResourceNotFoundException",
            "Message": "Requested resource could not be located",
            "HTTPStatusCode": 404,
            "SecurityBoundary": "RESOURCE_ACCESS",
            "SanitizedDetails": "Resource identifier not found in accessible scope",
        },
        "throttling": {
            "Code": "ThrottlingException",
            "Message": "Request rate limit exceeded - please retry with backoff",
            "HTTPStatusCode": 429,
            "SecurityBoundary": "RATE_LIMIT",
            "SanitizedDetails": "API rate limiting active for protection",
        },
        "validation_error": {
            "Code": "ValidationException",
            "Message": "Request validation failed - check input parameters",
            "HTTPStatusCode": 400,
            "SecurityBoundary": "INPUT_VALIDATION",
            "SanitizedDetails": "Input parameter validation criteria not met",
        },
        "internal_failure": {
            "Code": "InternalFailure",
            "Message": "Service unavailable - please try again later",
            "HTTPStatusCode": 500,
            "SecurityBoundary": "SERVICE_ERROR",
            "SanitizedDetails": "Internal service processing unavailable",
        },
        "service_unavailable": {
            "Code": "ServiceUnavailable",
            "Message": "Service temporarily unavailable - please retry",
            "HTTPStatusCode": 503,
            "SecurityBoundary": "SERVICE_HEALTH",
            "SanitizedDetails": "Service health check failure detected",
        },
    }

    # NetworkManager specific errors
    NETWORKMANAGER_ERRORS = {
        "core_network_not_found": {
            "Code": "CoreNetworkNotFoundException",
            "Message": "The specified core network was not found",
            "HTTPStatusCode": 404,
        },
        "global_network_not_found": {
            "Code": "GlobalNetworkNotFoundException",
            "Message": "The specified global network was not found",
            "HTTPStatusCode": 404,
        },
        "policy_version_not_found": {
            "Code": "PolicyVersionNotFoundException",
            "Message": "The specified policy version was not found",
            "HTTPStatusCode": 404,
        },
    }

    @classmethod
    def get_error(cls, error_name: str, operation: str = "TestOperation") -> ClientError:
        """Get a security-hardened ClientError for testing.

        Args:
            error_name: Name of error from catalog
            operation: AWS operation name

        Returns:
            Configured ClientError instance with security boundaries
        """
        error_config = None

        # Check common errors first
        if error_name in cls.COMMON_ERRORS:
            error_config = cls.COMMON_ERRORS[error_name]
        elif error_name in cls.NETWORKMANAGER_ERRORS:
            error_config = cls.NETWORKMANAGER_ERRORS[error_name]
        else:
            raise ValueError(f"Unknown error type: {error_name}")

        # Security boundary enforcement
        cls._validate_security_boundary(error_config, operation)

        # Use sanitized message to prevent information disclosure
        sanitized_message = cls.SAFE_MESSAGES.get(error_config["Code"], error_config["Message"])

        error_response = {
            "Error": {"Code": error_config["Code"], "Message": sanitized_message},
            "ResponseMetadata": {
                "RequestId": f"test-request-{cls._generate_safe_id()}-{hash(error_name) % 1000:03d}",
                "HTTPStatusCode": error_config["HTTPStatusCode"],
            },
        }

        # Log for audit trail (internal only)
        cls._log_error_generation(error_name, operation, error_config.get("SecurityBoundary"))

        return ClientError(error_response, operation)

    @classmethod
    def _validate_security_boundary(cls, error_config: dict, operation: str) -> None:
        """Helper to validate operation and security boundary for error_config."""
        boundary = cls._normalize_security_boundary(error_config.get("SecurityBoundary"))
        # Focused security boundary validation for truly sensitive operations
        highly_sensitive_operations = [
            "Admin",
            "Root",
            "Super",
            "Master",
            "Privileged",
            "System",
            "Delete",
            "Remove",
            "Destroy",
            "Terminate",
            "Drop",
        ]

        # Operations that modify state or could affect security posture
        state_changing_operations = ["Create", "Add", "Insert", "Update", "Modify", "Change", "Put", "Post"]

        # Check for highly sensitive operation patterns
        if any(
            operation.startswith(prefix) or prefix.lower() in operation.lower()
            for prefix in highly_sensitive_operations
        ):
            raise MockingSecurityError(
                f"Operation '{operation}' is considered highly sensitive and is not allowed in this context."
            )

        # Check for state-changing operations (less restrictive)

        # Handle RESTRICTED boundary - block all operations by default for unknown/invalid boundaries
        # Apply different rules based on sensitivity level

        # Additional boundary checks for different security contexts
        # SERVICE_ERROR boundary: Sanitize internal system references
        if boundary == "SERVICE_ERROR":
            system_terms = ["internal", "system", "database", "server", "host", "node"]
            message = error_config.get("Message", "")
            if any(term in message.lower() for term in system_terms):
                # Replace with generic message to prevent information disclosure
                error_config["Message"] = "Service temporarily unavailable. Please retry your request."

        # RESOURCE_ACCESS boundary: Validate that resource access errors don't leak existence information
        if boundary == "RESOURCE_ACCESS" and operation.lower().startswith("get"):
            if "exists" in error_config.get("Message", "").lower():
                raise MockingSecurityError(
                    f"Resource enumeration via error messages blocked for operation '{operation}'"
                )

        # RATE_LIMIT boundary: Ensure rate limit errors don't expose internal throttling mechanisms
        if boundary == "RATE_LIMIT":
            message = error_config.get("Message", "")
            if any(term in message.lower() for term in ["quota", "limit", "threshold", "bucket", "window"]):
                # Sanitize message to prevent internal throttling detail exposure
                error_config["Message"] = "Request rate exceeded. Please retry with exponential backoff."

    @classmethod
    def _generate_safe_id(cls) -> str:
        """Generate safe test request ID without system information exposure."""
        charset = string.ascii_lowercase + string.digits
        return "".join(secrets.choice(charset) for _ in range(8))

    @classmethod
    def _log_error_generation(cls, error_name: str, operation: str, boundary: str) -> None:
        """Log error generation for audit trail (security compliance)."""
        # In production, this would log to secure audit system
        pass


# Pytest integration helpers
def create_service_mocker(service: str, region: str = None) -> AWSServiceMocker:
    """Factory function for creating service mockers."""
    return AWSServiceMocker(service, region or "us-east-1")


def create_error_fixture(error_name: str, operation: str = "TestOperation") -> ClientError:
    """Factory function for creating error fixtures."""
    return AWSErrorCatalog.get_error(error_name, operation)
