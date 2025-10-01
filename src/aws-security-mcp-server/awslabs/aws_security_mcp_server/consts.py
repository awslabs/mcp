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

"""Constants for AWS Security MCP Server."""

# Server configuration
SERVER_NAME = "aws-security-mcp"
SERVER_VERSION = "0.1.0"

# AWS configuration
DEFAULT_AWS_PROFILE = "default"

# Tool names
TOOL_HEALTH_CHECK = "health_check"
TOOL_LIST_GUARDDUTY_FINDINGS = "list_guardduty_findings"
TOOL_LIST_SECURITYHUB_FINDINGS = "list_securityhub_findings"

# Error messages
ERROR_NO_DETECTORS = "No GuardDuty detectors found"
ERROR_AWS_CONNECTION = "Failed to connect to AWS"
ERROR_GUARDDUTY_RETRIEVAL = "Failed to retrieve GuardDuty findings"
ERROR_SECURITYHUB_RETRIEVAL = "Failed to retrieve Security Hub findings"

# Log configuration
LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
