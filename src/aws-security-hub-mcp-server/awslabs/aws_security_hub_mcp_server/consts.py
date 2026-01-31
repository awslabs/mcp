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
"""Constants for AWS Security Hub MCP Server."""

# Default configuration values
DEFAULT_AWS_REGION = "us-east-1"
DEFAULT_MAX_RESULTS = 50
DEFAULT_DAYS_BACK = 30
DEFAULT_LOG_LEVEL = "WARNING"

# AWS Security Hub API limits
AWS_MAX_RESULTS_PER_PAGE = 100
MAX_PAGINATION_PAGES = 50

# Security score calculation weights
SEVERITY_WEIGHTS = {
    "CRITICAL": 10,
    "HIGH": 7,
    "MEDIUM": 4,
    "LOW": 2,
    "INFORMATIONAL": 1,
}

# Environment variable names
ENV_AWS_PROFILE = "AWS_PROFILE"
ENV_AWS_REGION = "AWS_REGION"
ENV_LOG_LEVEL = "FASTMCP_LOG_LEVEL"
ENV_MAX_RESULTS = "SECURITY_HUB_MAX_RESULTS"
