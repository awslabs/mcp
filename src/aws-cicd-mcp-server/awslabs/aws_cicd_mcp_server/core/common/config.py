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

"""Configuration management for AWS CI/CD MCP Server."""

import os
from pathlib import Path

# Logging configuration
FASTMCP_LOG_LEVEL = os.getenv('FASTMCP_LOG_LEVEL', 'INFO')

# AWS configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
AWS_PROFILE = os.getenv('AWS_PROFILE')

# Read-only mode
READ_ONLY_MODE = os.getenv('CICD_READ_ONLY_MODE', 'true').lower() == 'true'

def get_server_directory() -> Path:
    """Get the server directory for logs and cache."""
    return Path.home() / '.aws-cicd-mcp-server'
