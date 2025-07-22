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

"""Standardized error handling utilities for Bedrock Advisor.

This module provides a consistent approach to error handling across
the application, including error logging, formatting, and response generation.
It ensures that all errors are handled in a uniform way, providing clear
and helpful information to users and developers.
"""

import json
import traceback
from typing import Any, Dict, List, Optional

import structlog
from pydantic import ValidationError

from .errors import (
    BedrockAdvisorError,
    ConfigurationError,
    InvalidCriteriaError,
    ModelNotFoundError,
    RateLimitExceededError,
    RegionNotSupportedError,
    ServiceUnavailableError,
)
from .errors import (
    ValidationError as CustomValidationError,
)

logger = structlog.get_logger(__name__)


class ErrorHandler:
    """Centralized error handler for consistent error processing.

    This class provides methods for handling different types of errors,
    generating standardized error responses, and logging error details
    with appropriate severity levels.
    """

    @staticmethod
    def handle_exception(
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle any exception and generate a standardized error response.

        This method processes exceptions, logs appropriate information,
        and generates a user-friendly error response with troubleshooting
        guidance tailored to the specific error type.

        Args:
            exception: The exception to handle
            context: Additional context information about the error
            tool_name: Name of the tool where the error occurred

        Returns:
            Dict[str, Any]: Standardized error response with troubleshooting guidance
        """
        context = context or {}
        error_context = {
            "error_type": type(exception).__name__,
            "tool_name": tool_name,
            **context,
        }

        # Log the error with appropriate context
        if isinstance(exception, BedrockAdvisorError):
            # For custom errors, use the details from the error
            logger.error(
                "Application error",
                error_message=str(exception),
                error_code=getattr(exception, "error_code", "UNKNOWN"),
                details=getattr(exception, "details", {}),
                **error_context,
            )
        else:
            # For unexpected errors, include stack trace
            logger.error(
                "Unexpected error",
                error_message=str(exception),
                traceback=traceback.format_exc(),
                **error_context,
            )

        # Generate standardized error response
        return ErrorHandler._create_error_response(exception, tool_name)

    @staticmethod
    def _create_error_response(
        error: Exception, tool_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a detailed error response with troubleshooting guidance.

        Args:
            error: The exception to convert to a response
            tool_name: Name of the tool where the error occurred

        Returns:
            Dict[str, Any]: Structured error response
        """
        error_response = {
            "error": type(error).__name__,
            "message": str(error),
            "success": False,
        }

        if tool_name:
            error_response["tool"] = tool_name

        # Include custom error details if available
        if isinstance(error, BedrockAdvisorError):
            error_response.update(error.to_dict())

        # Add troubleshooting guidance based on error type
        error_response["troubleshooting"] = ErrorHandler._get_troubleshooting_guidance(
            error
        )

        return error_response

    @staticmethod
    def _get_troubleshooting_guidance(error: Exception) -> List[str]:
        """Get specific troubleshooting guidance based on error type.

        This method provides detailed, actionable troubleshooting steps
        tailored to the specific error type and context. The guidance
        includes specific commands to run, parameters to check, and
        alternative approaches to try.

        Args:
            error: The exception to provide guidance for

        Returns:
            List[str]: List of troubleshooting steps
        """
        if isinstance(error, ModelNotFoundError):
            available_models = error.details.get("available_models", [])
            guidance = [
                f"Error: The model ID '{error.details.get('model_id', 'unknown')}' could not be found.",
                "Check that the model ID is spelled correctly and includes the version suffix (e.g., ':0').",
                "Verify that the model is available in your target region using the list_models tool.",
                "Try refreshing the model data with the refresh_models tool to get the latest available models.",
            ]

            if available_models:
                similar_models = [
                    m
                    for m in available_models
                    if any(
                        part in m
                        for part in error.details.get("model_id", "").split(".")
                    )
                ]
                if similar_models:
                    guidance.append(
                        f"Similar models you might be looking for: {', '.join(similar_models[:3])}"
                    )
                guidance.append(
                    f"Available models include: {', '.join(available_models[:5])}"
                    + (
                        f" and {len(available_models) - 5} more"
                        if len(available_models) > 5
                        else ""
                    )
                )

            return guidance
        elif isinstance(error, ServiceUnavailableError):
            service = error.details.get("service", "unknown")
            guidance = [
                f"Error: The {service} service is currently unavailable.",
                "Check your AWS credentials are correctly configured and have the necessary permissions.",
                "Verify your network connectivity to AWS services.",
                "The service might be experiencing temporary issues. Try again in a few minutes.",
            ]

            # Add retry guidance if available
            retry_after = error.details.get("retry_after_seconds")
            if retry_after:
                guidance.append(
                    f"Wait at least {retry_after} seconds before retrying the request."
                )

            if service.lower() == "bedrock":
                guidance.append(
                    "Use the refresh_models tool with force_refresh=false to use cached data instead."
                )
                guidance.append(
                    "Check the AWS Service Health Dashboard to see if there are any known issues with Bedrock."
                )

            return guidance
        elif isinstance(error, (ValidationError, CustomValidationError)):
            field_info = ""
            if hasattr(error, "details") and error.details:
                if "field" in error.details:
                    field_info = f" for field '{error.details['field']}'"
                if "field_path" in error.details:
                    field_info = f" at path '{error.details['field_path']}'"

            guidance = [
                f"Error: Input validation failed{field_info}.",
                "Check that all required parameters are provided in your request.",
                "Verify that parameter values match the expected types and formats.",
            ]

            if hasattr(error, "details") and error.details:
                if (
                    "provided_value" in error.details
                    and "valid_values" in error.details
                ):
                    guidance.append(
                        f"You provided '{error.details['provided_value']}', but valid values are: {', '.join(str(v) for v in error.details['valid_values'])}."
                    )
                elif "validation_errors" in error.details:
                    for i, ve in enumerate(error.details["validation_errors"][:3]):
                        guidance.append(f"Validation error {i + 1}: {ve}")

            return guidance

        elif isinstance(error, InvalidCriteriaError):
            field = error.details.get("field", "unknown")
            value = error.details.get("provided_value", "unknown")
            valid_values = error.details.get("valid_values", [])

            guidance = [
                f"Error: Invalid criteria for field '{field}'.",
                f"You provided '{value}', which is not valid for this field.",
            ]

            if valid_values:
                guidance.append(
                    f"Valid values for '{field}' are: {', '.join(str(v) for v in valid_values)}."
                )

            guidance.extend(
                [
                    "Check the API documentation for the correct parameter format and allowed values.",
                    "Ensure that your criteria are consistent (e.g., min_value should be less than max_value).",
                ]
            )

            return guidance
        elif isinstance(error, RegionNotSupportedError):
            region = error.details.get("region", "unknown")
            regions = error.details.get("supported_regions", [])

            guidance = [
                f"Error: The region '{region}' is not supported for this operation."
            ]

            if regions:
                guidance.append(
                    f"Supported regions: {', '.join(regions[:5])}"
                    + (f" and {len(regions) - 5} more" if len(regions) > 5 else "")
                )
                guidance.append("Try using one of the supported regions listed above.")
            else:
                guidance.extend(
                    [
                        "Check that the region name is spelled correctly (e.g., 'us-east-1', not 'us_east_1').",
                        "Verify that the region is supported by AWS Bedrock using the AWS documentation.",
                        "Use the list_models tool to see which regions are available for each model.",
                    ]
                )

            guidance.append(
                "Note that not all Bedrock models are available in all AWS regions."
            )

            return guidance
        elif isinstance(error, RateLimitExceededError):
            limit = error.details.get("rate_limit", "unknown")
            window = error.details.get("window_seconds", "unknown")
            retry_after = error.details.get("retry_after_seconds")

            guidance = [
                f"Error: Rate limit exceeded. The limit is {limit} requests per {window} seconds."
            ]

            if retry_after:
                guidance.append(
                    f"Wait at least {retry_after} seconds before retrying the request."
                )

            guidance.extend(
                [
                    "Implement exponential backoff in your client code to handle rate limiting gracefully.",
                    "Consider reducing the frequency of your requests or batching multiple operations together.",
                    "Use caching strategies to reduce the number of API calls for frequently accessed data.",
                ]
            )

            return guidance
        elif isinstance(error, ConfigurationError):
            config_key = error.details.get("config_key", "unknown")
            expected_type = error.details.get("expected_type", "appropriate type")

            guidance = [
                f"Error: Configuration error for '{config_key}'.",
                f"The configuration value should be of type {expected_type}.",
                "Check your configuration settings and ensure all required values are provided.",
                "Verify that environment variables are set correctly if using environment-based configuration.",
                "Refer to the documentation for the correct configuration format and required values.",
            ]

            return guidance
        else:
            # Enhanced generic guidance for unexpected errors
            error_type = type(error).__name__
            error_msg = str(error)

            guidance = [
                f"Error: An unexpected {error_type} occurred: {error_msg}",
                "Try the operation again to see if it was a transient issue.",
                "Check all input parameters for correctness and completeness.",
                "Verify that your AWS credentials have the necessary permissions for this operation.",
            ]

            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                guidance.append(
                    "The operation may have timed out. Try again with a longer timeout or smaller request."
                )
            elif "memory" in error_msg.lower():
                guidance.append(
                    "The operation may have exceeded memory limits. Try with a smaller request size."
                )
            elif "permission" in error_msg.lower() or "access" in error_msg.lower():
                guidance.append(
                    "Check that your IAM permissions include the necessary actions for Bedrock."
                )

            guidance.append(
                "If the issue persists, contact support with the full error details shown above."
            )

            return guidance

    @staticmethod
    def format_validation_error(error: ValidationError) -> Dict[str, Any]:
        """Format a Pydantic validation error into a structured response.

        This method converts Pydantic validation errors into a user-friendly
        format with detailed information about what went wrong and how to fix it.
        It includes the specific location of each error, the error message,
        and the error type.

        Args:
            error: Pydantic ValidationError

        Returns:
            Dict[str, Any]: Structured validation error details
        """
        errors = []
        for e in error.errors():
            errors.append(
                {
                    "loc": " -> ".join(str(loc_part) for loc_part in e["loc"]),
                    "msg": e["msg"],
                    "type": e["type"],
                }
            )

        # Create more specific troubleshooting guidance based on error types
        troubleshooting = [
            "Error: Input validation failed. Please check your request parameters."
        ]

        # Add specific guidance based on error types
        error_types = set(e["type"] for e in error.errors())

        if "missing" in error_types:
            troubleshooting.append(
                "Required fields are missing from your request. Check the API documentation for required parameters."
            )

        if "type_error" in error_types:
            troubleshooting.append(
                "Some fields have incorrect data types. Ensure values match the expected types (e.g., numbers for numeric fields)."
            )

        if "value_error" in error_types:
            troubleshooting.append(
                "Some field values are invalid. Check that values are within allowed ranges or formats."
            )

        if "enum" in error_types:
            troubleshooting.append(
                "Some fields contain values not in the allowed set. Check the API documentation for valid enum values."
            )

        # Add specific field guidance for up to 3 errors
        for i, e in enumerate(error.errors()[:3]):
            field_path = " -> ".join(str(loc_part) for loc_part in e["loc"])
            troubleshooting.append(f"Field '{field_path}': {e['msg']}")

        return {
            "error": "ValidationError",
            "message": "Input validation failed",
            "success": False,
            "details": {"validation_errors": errors},
            "troubleshooting": troubleshooting,
        }

    @staticmethod
    def safe_json_response(data: Dict[str, Any]) -> str:
        """Safely convert data to JSON string, handling serialization errors.

        Args:
            data: Data to convert to JSON

        Returns:
            str: JSON string representation of the data
        """
        try:
            return json.dumps(data, indent=2, default=str)
        except Exception as e:
            logger.error(
                "JSON serialization error", error=str(e), data_type=type(data).__name__
            )
            error_response = {
                "error": "SerializationError",
                "message": f"Failed to serialize response: {str(e)}",
                "success": False,
            }
            return json.dumps(error_response, indent=2)
