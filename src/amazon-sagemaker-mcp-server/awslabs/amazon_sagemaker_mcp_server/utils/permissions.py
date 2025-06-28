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

"""Permission utilities for Amazon SageMaker MCP Server."""

import os


class PermissionError(Exception):
    """Exception raised when required permissions are not available."""
    pass


def require_write_access():
    """Require write access to be enabled."""
    if not is_write_access_enabled():
        raise PermissionError(
            "Write access is required for this operation. "
            "Please run the server with --allow-write flag."
        )


def require_sensitive_data_access():
    """Require sensitive data access to be enabled."""
    if not is_sensitive_data_access_enabled():
        raise PermissionError(
            "Sensitive data access is required for this operation. "
            "Please run the server with --allow-sensitive-data-access flag."
        )


def is_write_access_enabled() -> bool:
    """Check if write access is enabled."""
    return os.getenv('ALLOW_WRITE', 'false').lower() == 'true'


def is_sensitive_data_access_enabled() -> bool:
    """Check if sensitive data access is enabled."""
    return os.getenv('ALLOW_SENSITIVE_DATA_ACCESS', 'false').lower() == 'true'


def get_permission_summary() -> dict:
    """Get a summary of current permissions."""
    return {
        'write_access': is_write_access_enabled(),
        'sensitive_data_access': is_sensitive_data_access_enabled(),
        'read_only_mode': not is_write_access_enabled()
    }
