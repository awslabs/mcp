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
"""Constants for the AWS Support MCP Server."""

from enum import Enum
from typing import Dict, Tuple

# Default configuration values
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_MODE = "standard"
DEFAULT_CONNECT_TIMEOUT = 30  # seconds
DEFAULT_READ_TIMEOUT = 10  # seconds


# Case status values
class CaseStatus(str, Enum):
    """Status values for AWS Support cases."""

    OPENED = "opened"
    PENDING_CUSTOMER_ACTION = "pending-customer-action"
    RESOLVED = "resolved"
    UNASSIGNED = "unassigned"
    WORK_IN_PROGRESS = "work-in-progress"
    CLOSED = "closed"


# Issue types
class IssueType(str, Enum):
    """Issue types for AWS Support cases."""

    TECHNICAL = "technical"
    ACCOUNT_AND_BILLING = "account-and-billing"
    SERVICE_LIMIT = "service-limit"


# Error codes
class ErrorCode(str, Enum):
    """AWS Support API error codes."""

    SUBSCRIPTION_REQUIRED = "SubscriptionRequiredException"
    ACCESS_DENIED = "AccessDeniedException"
    CASE_NOT_FOUND = "CaseIdNotFound"
    THROTTLING = "ThrottlingException"
    TOO_MANY_REQUESTS = "TooManyRequestsException"
    INTERNAL_SERVER = "InternalServerError"


# Default values
DEFAULT_REGION = "us-east-1"
DEFAULT_LANGUAGE = "en"
DEFAULT_ISSUE_TYPE = IssueType.TECHNICAL.value

# Language name mapping for better display
LANGUAGE_NAMES: Dict[str, Tuple[str, str]] = {
    "en": ("English", "English"),
    "ja": ("Japanese", "日本語"),
    "zh": ("Chinese", "中文"),
    "ko": ("Korean", "한국어"),
    "es": ("Spanish", "Español"),
    "fr": ("French", "Français"),
    "pt": ("Portuguese", "Português"),
    "tr": ("Turkish", "Türkçe"),
}

# Markdown templates
CASE_SUMMARY_TEMPLATE = """# Support Case Summary

{case_details}"""

# API endpoints and configuration
API_TIMEOUT = 30  # seconds

# Error messages
ERROR_SUBSCRIPTION_REQUIRED = (
    "AWS Support API access requires a Business, Enterprise On-Ramp, or Enterprise Support plan."
)
ERROR_AUTHENTICATION_FAILED = "Failed to authenticate with AWS Support API."
ERROR_CASE_NOT_FOUND = "The specified support case could not be found."
ERROR_RATE_LIMIT_EXCEEDED = "Rate limit exceeded. Please try again later."
ERROR_INTERNAL_SERVER = "An internal server error occurred."

# Error code to message mapping
ERROR_CODE_MAP = {
    ErrorCode.SUBSCRIPTION_REQUIRED: ERROR_SUBSCRIPTION_REQUIRED,
    ErrorCode.ACCESS_DENIED: ERROR_AUTHENTICATION_FAILED,
    ErrorCode.CASE_NOT_FOUND: ERROR_CASE_NOT_FOUND,
    ErrorCode.THROTTLING: ERROR_RATE_LIMIT_EXCEEDED,
    ErrorCode.TOO_MANY_REQUESTS: ERROR_RATE_LIMIT_EXCEEDED,
    ErrorCode.INTERNAL_SERVER: ERROR_INTERNAL_SERVER,
}

# HTTP status codes for error types
ERROR_STATUS_CODES = {
    ErrorCode.ACCESS_DENIED: 403,
    ErrorCode.CASE_NOT_FOUND: 404,
    ErrorCode.THROTTLING: 429,
    ErrorCode.TOO_MANY_REQUESTS: 429,
    ErrorCode.INTERNAL_SERVER: 500,
}

# Maximum number of results for pagination
MAX_RESULTS_PER_PAGE = 100

# Languages allowed for Case Creation
PERMITTED_LANGUAGE_CODES = ["en", "ja", "zh", "es", "pt", "fr", "ko", "tr"]
