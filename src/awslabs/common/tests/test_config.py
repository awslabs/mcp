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

"""Tests for shared configuration utilities."""

import os
from awslabs.common.config import disabled_tools, tool_enabled


class TestToolDisabling:
    """Test cases for tool disabling functionality."""

    def test_no_disabled_tools_by_default(self):
        """Test that no tools are disabled when environment variable not set."""
        # Ensure env var is not set
        os.environ.pop('DISABLED_TOOLS', None)
        assert disabled_tools() == set()
        assert tool_enabled('ExecuteTerraformCommand')
        assert tool_enabled('RunCheckovScan')

    def test_single_disabled_tool(self):
        """Test disabling a single tool."""
        os.environ['DISABLED_TOOLS'] = 'ExecuteTerraformCommand'
        disabled = disabled_tools()
        assert 'ExecuteTerraformCommand' in disabled
        assert len(disabled) == 1
        assert not tool_enabled('ExecuteTerraformCommand')
        assert tool_enabled('RunCheckovScan')

    def test_multiple_disabled_tools(self):
        """Test disabling multiple tools."""
        os.environ['DISABLED_TOOLS'] = 'ExecuteTerraformCommand,RunCheckovScan'
        disabled = disabled_tools()
        assert 'ExecuteTerraformCommand' in disabled
        assert 'RunCheckovScan' in disabled
        assert len(disabled) == 2
        assert not tool_enabled('ExecuteTerraformCommand')
        assert not tool_enabled('RunCheckovScan')
        assert tool_enabled('SearchAwsProviderDocs')

    def test_whitespace_handling(self):
        """Test that whitespace is properly handled."""
        os.environ['DISABLED_TOOLS'] = ' ExecuteTerraformCommand , RunCheckovScan '
        disabled = disabled_tools()
        assert 'ExecuteTerraformCommand' in disabled
        assert 'RunCheckovScan' in disabled
        assert len(disabled) == 2

    def test_empty_tool_names_ignored(self):
        """Test that empty tool names are ignored."""
        os.environ['DISABLED_TOOLS'] = 'ExecuteTerraformCommand,,RunCheckovScan,'
        disabled = disabled_tools()
        assert len(disabled) == 2
        assert 'ExecuteTerraformCommand' in disabled
        assert 'RunCheckovScan' in disabled

    def test_empty_environment_variable(self):
        """Test handling of empty environment variable."""
        os.environ['DISABLED_TOOLS'] = ''
        assert disabled_tools() == set()
        assert tool_enabled('ExecuteTerraformCommand')

    def test_only_commas_and_whitespace(self):
        """Test handling of environment variable with only commas and whitespace."""
        os.environ['DISABLED_TOOLS'] = ' , , , '
        assert disabled_tools() == set()
        assert tool_enabled('ExecuteTerraformCommand')

    def test_case_sensitive_tool_names(self):
        """Test that tool names are case sensitive."""
        os.environ['DISABLED_TOOLS'] = 'executeterraformcommand'  # lowercase
        disabled = disabled_tools()
        assert 'executeterraformcommand' in disabled
        assert not tool_enabled('executeterraformcommand')
        assert tool_enabled('ExecuteTerraformCommand')  # uppercase - should be enabled

    def teardown_method(self):
        """Clean up environment variables after each test."""
        os.environ.pop('DISABLED_TOOLS', None)
