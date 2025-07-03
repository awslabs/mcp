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

"""Context management for DataZone MCP Server."""


class Context:
    """Context class for DataZone MCP Server."""

    _readonly = True  # Default to read-only for security

    @classmethod
    def initialize(cls, readonly: bool = True):
        """Initialize the context.

        Args:
            readonly: Whether to run in readonly mode (default: True)
        """
        cls._readonly = readonly

    @classmethod
    def readonly_mode(cls) -> bool:
        """Check if the server is running in readonly mode.

        Returns:
            True if readonly mode is enabled, False otherwise
        """
        return cls._readonly

    @classmethod
    def check_write_permission(cls, operation_name: str):
        """Check if write operations are allowed.

        Args:
            operation_name: Name of the operation being attempted

        Raises:
            ValueError: If the server is in read-only mode and write operation is attempted
        """
        if cls._readonly:
            raise ValueError(
                f'Operation "{operation_name}" not allowed: Server is configured in read-only mode. '
                'To enable write operations, restart the server with --allow-writes parameter.'
            ) 