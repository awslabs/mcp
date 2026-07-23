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

"""
Security utilities for the EC2 MCP Server.
"""

import functools
import json
import logging
import os.path
import re
from typing import Any, Awaitable, Callable, Dict, Literal, Optional, Set

logger = logging.getLogger(__name__)

# Define permission types as constants
PERMISSION_WRITE = "write"
PERMISSION_SENSITIVE_DATA = "sensitive-data"
PERMISSION_NONE = "none"

# Define permission type
PermissionType = Literal["write", "sensitive-data", "none"]


class SecurityError(Exception):
    """Exception raised for security-related errors."""

    pass


class ValidationError(Exception):
    """Exception raised for validation errors."""

    pass


def validate_instance_id(instance_id: str) -> bool:
    """
    Validates EC2 instance ID format.

    Args:
        instance_id: The instance ID to validate

    Returns:
        bool: Whether the instance ID is valid

    Raises:
        ValidationError: If the instance ID format is invalid
    """
    pattern = r"^i-[0-9a-f]{8,17}$"
    if not re.match(pattern, instance_id):
        raise ValidationError(
            "Invalid instance ID format. "
            "Must be in format 'i-' followed by 8-17 hexadecimal characters."
        )
    return True


def validate_security_group_id(sg_id: str) -> bool:
    """
    Validates security group ID format.

    Args:
        sg_id: The security group ID to validate

    Returns:
        bool: Whether the security group ID is valid

    Raises:
        ValidationError: If the security group ID format is invalid
    """
    pattern = r"^sg-[0-9a-f]{8,17}$"
    if not re.match(pattern, sg_id):
        raise ValidationError(
            "Invalid security group ID format. "
            "Must be in format 'sg-' followed by 8-17 hexadecimal characters."
        )
    return True


def validate_vpc_id(vpc_id: str) -> bool:
    """
    Validates VPC ID format.

    Args:
        vpc_id: The VPC ID to validate

    Returns:
        bool: Whether the VPC ID is valid

    Raises:
        ValidationError: If the VPC ID format is invalid
    """
    pattern = r"^vpc-[0-9a-f]{8,17}$"
    if not re.match(pattern, vpc_id):
        raise ValidationError(
            f"VPC ID '{vpc_id}' has invalid format. "
            "Must be in format 'vpc-' followed by 8-17 hexadecimal characters."
        )
    return True


def validate_subnet_id(subnet_id: str) -> bool:
    """
    Validates subnet ID format.

    Args:
        subnet_id: The subnet ID to validate

    Returns:
        bool: Whether the subnet ID is valid

    Raises:
        ValidationError: If the subnet ID format is invalid
    """
    pattern = r"^subnet-[0-9a-f]{8,17}$"
    if not re.match(pattern, subnet_id):
        raise ValidationError(
            f"Subnet ID '{subnet_id}' has invalid format. "
            "Must be in format 'subnet-' followed by 8-17 hexadecimal characters."
        )
    return True


def validate_ami_id(ami_id: str) -> bool:
    """
    Validates AMI ID format.

    Args:
        ami_id: The AMI ID to validate

    Returns:
        bool: Whether the AMI ID is valid

    Raises:
        ValidationError: If the AMI ID format is invalid
    """
    pattern = r"^ami-[0-9a-f]{8,17}$"
    if not re.match(pattern, ami_id):
        raise ValidationError(
            f"AMI ID '{ami_id}' has invalid format. "
            "Must be in format 'ami-' followed by 8-17 hexadecimal characters."
        )
    return True


def validate_volume_id(volume_id: str) -> bool:
    """
    Validates EBS volume ID format.

    Args:
        volume_id: The volume ID to validate

    Returns:
        bool: Whether the volume ID is valid

    Raises:
        ValidationError: If the volume ID format is invalid
    """
    pattern = r"^vol-[0-9a-f]{8,17}$"
    if not re.match(pattern, volume_id):
        raise ValidationError(
            f"Volume ID '{volume_id}' has invalid format. "
            "Must be in format 'vol-' followed by 8-17 hexadecimal characters."
        )
    return True


def validate_key_pair_name(key_name: str) -> bool:
    """
    Validates key pair name format.

    Args:
        key_name: The key pair name to validate

    Returns:
        bool: Whether the key pair name is valid

    Raises:
        ValidationError: If the key pair name format is invalid
    """
    # AWS key pair names allow alphanumeric characters, spaces, and certain special characters
    pattern = r"^[a-zA-Z0-9\s._\-@]+$"
    if not re.match(pattern, key_name):
        raise ValidationError(
            "Invalid key pair name contains invalid characters. "
            "Only alphanumeric characters, spaces, dots, underscores, hyphens, and @ are allowed."
        )
    
    if len(key_name) > 255:
        raise ValidationError("Key pair name is too long. Maximum length is 255 characters.")
    
    return True


def check_permission(config: Dict[str, Any], permission_type: PermissionType) -> bool:
    """
    Checks if the specified permission is allowed based on configuration settings.

    Args:
        config: The MCP server configuration
        permission_type: The type of permission to check

    Returns:
        bool: Whether the operation is allowed

    Raises:
        SecurityError: If the operation is not allowed
    """
    if permission_type == PERMISSION_WRITE and not config.get("allow-write", False):
        raise SecurityError(
            "Write operations are disabled for security. "
            "Set ALLOW_WRITE=true in your environment to enable, "
            "but be aware of the security implications."
        )
    elif permission_type == PERMISSION_SENSITIVE_DATA and not config.get(
        "allow-sensitive-data", False
    ):
        raise SecurityError(
            "Access to sensitive data is not allowed without ALLOW_SENSITIVE_DATA=true "
            "in your environment due to potential exposure of sensitive information."
        )

    return True


class ResponseSanitizer:
    """Sanitizes responses to prevent sensitive information leakage."""

    # Patterns for sensitive data
    PATTERNS = {
        "aws_access_key": r"(?<![A-Z0-9])[A-Z0-9]{20}(?![A-Z0-9])",
        "aws_secret_key": r"(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])",
        "password": r"(?i)password\s*[=:]\s*[^\s]+",
        "private_key": r"-----BEGIN (?:RSA|DSA|EC|OPENSSH) PRIVATE KEY-----",
        "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "aws_account_id": r"\b\d{12}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b(?:\d{4}[- ]?){3}\d{4}\b",
        "phone": r"\b(?:\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b",
    }

    # Fields that are allowed in responses
    ALLOWED_FIELDS: Set[str] = {
        "status",
        "message",
        "instance_id",
        "instance_state",
        "instance_type",
        "public_ip",
        "private_ip",
        "security_groups",
        "key_name",
        "subnet_id",
        "vpc_id",
        "ami_id",
        "volume_id",
        "availability_zone",
        "error",
        "warnings",
        "resources",
        "guidance",
        "logs",
        "events",
        "templates",
        "infrastructure",
        "launch_time",
        "monitoring",
        "tags",
        "network_interfaces",
        "block_device_mappings",
    }

    @classmethod
    def sanitize(cls, response: Any) -> Any:
        """
        Sanitizes a response to remove sensitive information.

        Args:
            response: The response to sanitize

        Returns:
            Any: The sanitized response
        """
        if isinstance(response, dict):
            return cls._sanitize_dict(response)
        elif isinstance(response, list):
            return [cls.sanitize(item) for item in response]
        elif isinstance(response, str):
            return cls._sanitize_string(response)
        else:
            return response

    @classmethod
    def _sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitizes a dictionary.

        Args:
            data: The dictionary to sanitize

        Returns:
            Dict[str, Any]: The sanitized dictionary
        """
        result = {}
        for key, value in data.items():
            # Include all keys but sanitize values
            result[key] = cls.sanitize(value)
        return result

    @classmethod
    def _sanitize_string(cls, text: str) -> str:
        """
        Sanitizes a string to remove sensitive information.

        Args:
            text: The string to sanitize

        Returns:
            str: The sanitized string
        """
        for pattern_name, pattern in cls.PATTERNS.items():
            text = re.sub(pattern, f"[REDACTED {pattern_name.upper()}]", text)
        return text

    @classmethod
    def add_security_warning(cls, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adds security warnings for public resources in responses.

        Args:
            response: The response to modify

        Returns:
            Dict[str, Any]: The modified response
        """
        if isinstance(response, dict):
            # Check for public IP addresses
            if "public_ip" in response and response["public_ip"]:
                response["warnings"] = response.get("warnings", [])
                response["warnings"].append(
                    "WARNING: This instance has a public IP address. "
                    "Ensure appropriate security group rules are in place "
                    "to restrict access to only necessary ports and sources."
                )

        return response


def secure_tool(
    config: Dict[str, Any], permission_type: PermissionType, tool_name: Optional[str] = None
):
    """
    Decorator to secure a tool function with permission checks and response sanitization.

    Args:
        config: The MCP server configuration
        permission_type: The type of permission required for this tool
        tool_name: Optional name of the tool (for logging purposes)

    Returns:
        Decorator function that wraps the tool with security checks and response sanitization
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Validate security permissions
                check_permission(config, permission_type)
                # Call the original function if validation passes
                response = await func(*args, **kwargs)
                # Sanitize the response
                sanitized_response = ResponseSanitizer.sanitize(response)
                # Add warnings for public resources
                sanitized_response = ResponseSanitizer.add_security_warning(
                    sanitized_response
                )
                return sanitized_response
            except SecurityError as e:
                # Get tool name for logging
                log_tool_name = tool_name or func.__name__
                # Return error if validation fails
                logger.warning(f"Security validation failed for tool {log_tool_name}: {str(e)}")
                return {
                    "error": str(e),
                    "status": "failed",
                    "message": (
                        "Security validation failed. Please check your environment configuration."
                    ),
                }

        return wrapper

    return decorator