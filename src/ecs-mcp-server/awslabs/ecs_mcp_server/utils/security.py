# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""
Security utilities for the ECS MCP Server.
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


def validate_app_name(app_name: str) -> bool:
    """
    Validates application name to ensure it contains only allowed characters.

    Args:
        app_name: The application name to validate

    Returns:
        bool: Whether the name is valid

    Raises:
        ValidationError: If the name contains invalid characters
    """
    # Allow alphanumeric characters, hyphens, and underscores
    pattern = r"^[a-zA-Z0-9\-_]+$"
    if not re.match(pattern, app_name):
        raise ValidationError(
            f"Application name '{app_name}' contains invalid characters. "
            "Only alphanumeric characters, hyphens, and underscores are allowed."
        )
    return True


def validate_file_path(path: str) -> str:
    """
    Validates file path to prevent directory traversal attacks.

    Args:
        path: The file path to validate

    Returns:
        str: The normalized absolute path

    Raises:
        ValidationError: If the path is invalid or doesn't exist
    """
    # Convert to absolute path and normalize
    abs_path = os.path.abspath(os.path.normpath(path))

    # Check if the path exists
    if not os.path.exists(abs_path):
        raise ValidationError(f"Path '{path}' does not exist")

    # Check for suspicious path components that might indicate traversal attempts
    suspicious_patterns = [
        r"/\.\./",  # /../
        r"\\\.\.\\",  # \..\ (Windows)
        r"^\.\./",  # ../
        r"^\.\.\\",  # ..\ (Windows)
    ]

    for pattern in suspicious_patterns:
        if re.search(pattern, path):
            raise ValidationError(f"Path '{path}' contains suspicious traversal patterns")

    return abs_path


def validate_cloudformation_template(template_path: str) -> bool:
    """
    Validates a CloudFormation template against basic schema requirements.

    Args:
        template_path: Path to the CloudFormation template file

    Returns:
        bool: Whether the template is valid

    Raises:
        ValidationError: If the template is invalid
    """
    # First validate the file path
    validated_path = validate_file_path(template_path)

    # Read template file
    try:
        with open(validated_path, "r") as f:
            template_content = f.read()
    except Exception as e:
        raise ValidationError(f"Failed to read template file: {str(e)}") from e

    # Validate JSON format
    try:
        template = json.loads(template_content)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON in CloudFormation template: {str(e)}") from e

    # Basic CloudFormation template validation
    if not isinstance(template, dict):
        raise ValidationError("CloudFormation template must be a JSON object")

    # Check for required sections
    if "Resources" not in template:
        raise ValidationError("CloudFormation template must contain a 'Resources' section")

    # Check that Resources is a dictionary
    if not isinstance(template["Resources"], dict):
        raise ValidationError("'Resources' section must be a JSON object")

    # Check that at least one resource is defined
    if not template["Resources"]:
        raise ValidationError("CloudFormation template must define at least one resource")

    # Additional security checks could be added here

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
        "alb_url",
        "service_name",
        "cluster_name",
        "task_count",
        "desired_count",
        "events",
        "resources",
        "guidance",
        "error",
        "warnings",
        "templates",
        "deployment_status",
        "logs",
        "infrastructure",
        "containerization",
        "app_name",
        "app_path",
        "ecr_repository",
        "ecs_cluster",
        "ecs_service",
        "ecs_task_definition",
        "cloudformation_stack",
        "cloudformation_status",
        "cloudwatch_logs",
        "task_failures",
        "service_events",
        "image_pull_failures",
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
            # This is more permissive than the original implementation
            # which only included allowed fields
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
    def add_public_endpoint_warning(cls, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adds warnings for public endpoints in responses.

        Args:
            response: The response to modify

        Returns:
            Dict[str, Any]: The modified response
        """
        if isinstance(response, dict):
            # Check for ALB URL
            if "alb_url" in response:
                response["warnings"] = response.get("warnings", [])
                response["warnings"].append(
                    "WARNING: This ALB URL is publicly accessible. "
                    "Ensure appropriate security measures are in place "
                    "before sharing sensitive data."
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
                # Add warnings for public endpoints
                sanitized_response = ResponseSanitizer.add_public_endpoint_warning(
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
