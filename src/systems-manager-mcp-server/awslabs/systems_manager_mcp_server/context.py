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

"""Context management for AWS Systems Manager MCP Server."""

import os
from typing import Optional


class Context:
    """Global context for the Systems Manager MCP server."""

    _readonly: bool = False
    _aws_region: Optional[str] = None
    _aws_profile: Optional[str] = None
    _log_level: str = 'INFO'

    @classmethod
    def set_readonly(cls, readonly: bool) -> None:
        """Set the read-only mode for the server."""
        cls._readonly = readonly

    @classmethod
    def is_readonly(cls) -> bool:
        """Check if the server is in read-only mode."""
        return cls._readonly

    @classmethod
    def set_aws_region(cls, region: Optional[str]) -> None:
        """Set the default AWS region."""
        cls._aws_region = region

    @classmethod
    def get_aws_region(cls) -> Optional[str]:
        """Get the default AWS region."""
        return cls._aws_region or os.getenv('AWS_REGION')

    @classmethod
    def set_aws_profile(cls, profile: Optional[str]) -> None:
        """Set the default AWS profile."""
        cls._aws_profile = profile

    @classmethod
    def get_aws_profile(cls) -> Optional[str]:
        """Get the default AWS profile."""
        return cls._aws_profile or os.getenv('AWS_PROFILE')

    @classmethod
    def set_log_level(cls, log_level: str) -> None:
        """Set the log level."""
        cls._log_level = log_level

    @classmethod
    def get_log_level(cls) -> str:
        """Get the log level."""
        return cls._log_level

    @classmethod
    def initialize_from_env(cls) -> None:
        """Initialize context from environment variables."""
        cls._aws_region = os.getenv('AWS_REGION')
        cls._aws_profile = os.getenv('AWS_PROFILE')
        cls._log_level = os.getenv('FASTMCP_LOG_LEVEL', 'INFO')

        # Check for read-only mode from environment
        readonly_env = os.getenv('SSM_MCP_READONLY', 'false').lower()
        cls._readonly = readonly_env in ('true', '1', 'yes', 'on')
