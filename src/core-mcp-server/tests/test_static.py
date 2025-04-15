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
"""Tests for the static module."""

from importlib import resources
from pathlib import Path


class TestStatic:
    """Tests for the static module."""

    def test_prompt_understanding_import(self):
        """Test that PROMPT_UNDERSTANDING is imported correctly."""
        # Import the module
        from awslabs.core_mcp_server.static import PROMPT_UNDERSTANDING

        # Check that PROMPT_UNDERSTANDING is defined
        assert PROMPT_UNDERSTANDING is not None

        # Check that PROMPT_UNDERSTANDING is a string
        assert isinstance(PROMPT_UNDERSTANDING, str)

        # Check that PROMPT_UNDERSTANDING is not empty
        assert len(PROMPT_UNDERSTANDING) > 0

    def test_prompt_understanding_content(self):
        """Test that PROMPT_UNDERSTANDING contains expected content."""
        # Import the module
        from awslabs.core_mcp_server.static import PROMPT_UNDERSTANDING

        # Check that PROMPT_UNDERSTANDING contains expected sections
        assert '# AWSLABS.CORE-MCP-SERVER' in PROMPT_UNDERSTANDING
        assert 'Initial Query Analysis' in PROMPT_UNDERSTANDING
        assert 'AWS Service Mapping' in PROMPT_UNDERSTANDING
        assert 'Example Translation' in PROMPT_UNDERSTANDING
        assert 'Best Practices' in PROMPT_UNDERSTANDING
        assert 'Tool Usage Strategy' in PROMPT_UNDERSTANDING

    def test_prompt_understanding_file_exists(self):
        """Test that the PROMPT_UNDERSTANDING.md file exists."""
        # Check that the file exists using importlib.resources
        # Use resources.files().joinpath() to get the resource, then convert to string for Path
        resource = resources.files('awslabs.core_mcp_server.static').joinpath(
            'PROMPT_UNDERSTANDING.md'
        )
        file_path = Path(str(resource))
        assert file_path.exists()

    def test_prompt_understanding_file_content(self):
        """Test that the PROMPT_UNDERSTANDING.md file content matches the imported constant."""
        # Import the module
        from awslabs.core_mcp_server.static import PROMPT_UNDERSTANDING

        # Read the file content directly
        resource = resources.files('awslabs.core_mcp_server.static').joinpath(
            'PROMPT_UNDERSTANDING.md'
        )
        with resource.open('r', encoding='utf-8') as f:
            file_content = f.read()

        # Check that the file content matches the imported constant
        assert file_content == PROMPT_UNDERSTANDING
