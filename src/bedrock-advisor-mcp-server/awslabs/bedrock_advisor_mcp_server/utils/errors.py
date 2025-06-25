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

"""Custom exception classes for the Bedrock Advisor.

This module defines a hierarchy of custom exceptions that provide
detailed error information and context for better error handling
and debugging throughout the application.
"""

from typing import Any, Dict, Optional


class BedrockAdvisorError(Exception):
    """Base exception class for all Bedrock Advisor errors.

    Provides structured error information including error codes,
    detailed messages, and contextual data for debugging.
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """Initialize the error with detailed information.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional context and debugging information
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization."""
        result = {
            "error": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
        }

        if self.details:
            result["details"] = self.details

        if self.cause:
            result["cause"] = str(self.cause)

        return result


class ModelNotFoundError(BedrockAdvisorError):
    """Raised when a requested model cannot be found.

    This error occurs when trying to access a model by ID that
    doesn't exist in the model database or is not available.
    """

    def __init__(self, model_id: str, available_models: Optional[list] = None) -> None:
        """Initialize with model ID and optional list of available models.

        Args:
            model_id: The model ID that was not found
            available_models: List of available model IDs for reference
        """
        message = f"Model with ID '{model_id}' not found"
        details = {"model_id": model_id}

        if available_models:
            details["available_models"] = available_models
            message += f". Available models: {', '.join(available_models[:5])}"
            if len(available_models) > 5:
                message += f" and {len(available_models) - 5} more"

        super().__init__(message=message, error_code="MODEL_NOT_FOUND", details=details)


class InvalidCriteriaError(BedrockAdvisorError):
    """Raised when model selection criteria are invalid or inconsistent.

    This error occurs when the provided criteria for model recommendation
    or comparison contain invalid values, missing required fields, or
    conflicting requirements.
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        valid_values: Optional[list] = None,
    ) -> None:
        """Initialize with validation details.

        Args:
            message: Detailed error message
            field: Name of the invalid field
            value: The invalid value provided
            valid_values: List of valid values for the field
        """
        details = {}

        if field:
            details["field"] = field

        if value is not None:
            details["provided_value"] = value

        if valid_values:
            details["valid_values"] = valid_values

        super().__init__(
            message=message, error_code="INVALID_CRITERIA", details=details
        )


class RegionNotSupportedError(BedrockAdvisorError):
    """Raised when an unsupported AWS region is specified.

    This error occurs when trying to access model information or
    perform operations in a region that is not supported by
    Amazon Bedrock or the specific models.
    """

    def __init__(self, region: str, supported_regions: Optional[list] = None) -> None:
        """Initialize with region information.

        Args:
            region: The unsupported region
            supported_regions: List of supported regions
        """
        message = f"Region '{region}' is not supported"
        details = {"region": region}

        if supported_regions:
            details["supported_regions"] = supported_regions
            message += f". Supported regions: {', '.join(supported_regions)}"

        super().__init__(
            message=message, error_code="REGION_NOT_SUPPORTED", details=details
        )


class ValidationError(BedrockAdvisorError):
    """Raised when input validation fails.

    This error occurs when request data fails validation checks,
    such as invalid data types, out-of-range values, or malformed
    input structures.
    """

    def __init__(
        self,
        message: str,
        validation_errors: Optional[list] = None,
        field_path: Optional[str] = None,
    ) -> None:
        """Initialize with validation details.

        Args:
            message: Primary validation error message
            validation_errors: List of specific validation errors
            field_path: Path to the field that failed validation
        """
        details = {}

        if validation_errors:
            details["validation_errors"] = validation_errors

        if field_path:
            details["field_path"] = field_path

        super().__init__(
            message=message, error_code="VALIDATION_ERROR", details=details
        )


class ServiceUnavailableError(BedrockAdvisorError):
    """Raised when external services are unavailable.

    This error occurs when AWS services or other external dependencies
    are temporarily unavailable or experiencing issues.
    """

    def __init__(
        self,
        service: str,
        message: Optional[str] = None,
        retry_after: Optional[int] = None,
    ) -> None:
        """Initialize with service information.

        Args:
            service: Name of the unavailable service
            message: Optional detailed message
            retry_after: Suggested retry delay in seconds
        """
        error_message = message or f"Service '{service}' is currently unavailable"
        details = {"service": service}

        if retry_after:
            details["retry_after_seconds"] = retry_after
            error_message += f". Please retry after {retry_after} seconds"

        super().__init__(
            message=error_message, error_code="SERVICE_UNAVAILABLE", details=details
        )


class RateLimitExceededError(BedrockAdvisorError):
    """Raised when rate limits are exceeded.

    This error occurs when too many requests are made within
    a specified time window, triggering rate limiting protection.
    """

    def __init__(
        self, limit: int, window_seconds: int, retry_after: Optional[int] = None
    ) -> None:
        """Initialize with rate limit information.

        Args:
            limit: The rate limit that was exceeded
            window_seconds: Time window for the rate limit
            retry_after: Seconds to wait before retrying
        """
        message = f"Rate limit exceeded: {limit} requests per {window_seconds} seconds"
        details = {"rate_limit": limit, "window_seconds": window_seconds}

        if retry_after:
            details["retry_after_seconds"] = retry_after
            message += f". Retry after {retry_after} seconds"

        super().__init__(
            message=message, error_code="RATE_LIMIT_EXCEEDED", details=details
        )


class ConfigurationError(BedrockAdvisorError):
    """Raised when there are configuration issues.

    This error occurs when the server is misconfigured or
    required configuration values are missing or invalid.
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        expected_type: Optional[str] = None,
    ) -> None:
        """Initialize with configuration details.

        Args:
            message: Configuration error message
            config_key: The configuration key that has issues
            expected_type: Expected type for the configuration value
        """
        details = {}

        if config_key:
            details["config_key"] = config_key

        if expected_type:
            details["expected_type"] = expected_type

        super().__init__(
            message=message, error_code="CONFIGURATION_ERROR", details=details
        )
