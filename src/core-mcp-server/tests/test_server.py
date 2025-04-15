# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for the Core MCP Server."""

from awslabs.core_mcp_server.server import get_prompt_understanding
from awslabs.core_mcp_server.static import PROMPT_UNDERSTANDING


class TestPromptUnderstanding:
    """Tests for get_prompt_understanding function."""

    def test_get_prompt_understanding(self):
        """Test that get_prompt_understanding returns the correct content."""
        import asyncio

        result = asyncio.run(get_prompt_understanding())
        assert result == PROMPT_UNDERSTANDING
