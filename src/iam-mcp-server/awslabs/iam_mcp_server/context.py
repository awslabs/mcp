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

"""Context management for the AWS IAM MCP Server."""

from typing import Optional


class Context:
    """Context class for managing server state and configuration."""

    _readonly: bool = False
    _region: Optional[str] = None

    @classmethod
    def initialize(cls, readonly: bool = False, region: Optional[str] = None):
        """Initialize the context with configuration options.

        Args:
            readonly: Whether to run in read-only mode (prevents mutations)
            region: AWS region to use for operations
        """
        cls._readonly = readonly
        cls._region = region

    @classmethod
    def is_readonly(cls) -> bool:
        """Check if the server is running in read-only mode."""
        return cls._readonly

    @classmethod
    def get_region(cls) -> Optional[str]:
        """Get the configured AWS region."""
        return cls._region

    @classmethod
    def set_region(cls, region: str):
        """Set the AWS region."""
        cls._region = region

    @classmethod
    def set_readonly(cls, readonly: bool):
        """Set the read-only mode."""
        cls._readonly = readonly
