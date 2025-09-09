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

"""Context management for Database Migration Service MCP Server."""


class Context:
    """Context manager for DMS MCP Server state."""

    _readonly_mode = True  # Default to read-only mode

    @classmethod
    def initialize(cls, readonly: bool = True):
        """Initialize the context with readonly mode setting."""
        cls._readonly_mode = readonly

    @classmethod
    def readonly_mode(cls) -> bool:
        """Check if server is in readonly mode."""
        return cls._readonly_mode

    @classmethod
    def require_write_access(cls):
        """Check if write operations are allowed."""
        if cls._readonly_mode:
            raise ValueError(
                'Your DMS MCP server does not allow writes. To use write operations, change the MCP configuration to remove the --read-only-mode parameter.'
            )
