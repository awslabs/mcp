# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Tests for Windows compatibility in the diagrams-mcp-server."""

import os
import platform
import pytest
from awslabs.aws_diagram_mcp_server.diagrams_tools import generate_diagram


class TestWindowsCompatibility:
    """Tests for Windows compatibility in the diagrams-mcp-server."""

    @pytest.mark.asyncio
    async def test_timeout_mechanism(self, temp_workspace_dir):
        """Test that the timeout mechanism works on both Windows and Unix-like systems."""
        # Create a diagram code that will timeout (infinite loop)
        timeout_code = """
import time
with Diagram("Timeout Test", show=False):
    ELB("lb") >> EC2("web") >> RDS("userdb")
    # This will cause a timeout
    while True:
        time.sleep(0.1)
"""

        # Set a short timeout to speed up the test
        timeout = 2

        # Generate the diagram with the timeout code
        result = await generate_diagram(
            code=timeout_code,
            filename='timeout_test',
            timeout=timeout,
            workspace_dir=temp_workspace_dir,
        )

        # Check that the diagram generation timed out
        assert result.status == 'error'
        assert 'timed out' in result.message.lower()

    @pytest.mark.asyncio
    async def test_successful_diagram_generation(self, temp_workspace_dir):
        """Test that diagram generation works on both Windows and Unix-like systems."""
        # Create a simple diagram code
        simple_code = """with Diagram("Simple Test", show=False):
    ELB("lb") >> EC2("web") >> RDS("userdb")
"""

        # Generate the diagram
        result = await generate_diagram(
            code=simple_code,
            filename='simple_test',
            workspace_dir=temp_workspace_dir,
        )

        # Skip the test if Graphviz is not installed
        if result.status == 'error' and (
            'executablenotfound' in result.message.lower() or 'dot' in result.message.lower()
        ):
            pytest.skip('Graphviz not installed, skipping test')

        # Check that the diagram was generated successfully
        assert result.status == 'success'
        assert result.path is not None
        assert os.path.exists(result.path)
        assert result.path.endswith('.png')

    @pytest.mark.asyncio
    async def test_platform_specific_behavior(self, temp_workspace_dir):
        """Test that the platform-specific behavior works correctly."""
        # Create a diagram code that logs the platform
        platform_code = """
import platform
with Diagram("Platform Test", show=False):
    ELB("lb") >> EC2("web") >> RDS("userdb")
    # Log the platform for verification
    print(f"Running on platform: {platform.system()}")
"""

        # Generate the diagram
        result = await generate_diagram(
            code=platform_code,
            filename='platform_test',
            workspace_dir=temp_workspace_dir,
        )

        # Skip the test if Graphviz is not installed
        if result.status == 'error' and (
            'executablenotfound' in result.message.lower() or 'dot' in result.message.lower()
        ):
            pytest.skip('Graphviz not installed, skipping test')

        # Check that the diagram was generated successfully
        assert result.status == 'success'
        assert result.path is not None
        assert os.path.exists(result.path)
        assert result.path.endswith('.png')

        # Verify that the platform-specific code path was used
        current_platform = platform.system()
        print(f'Test running on platform: {current_platform}')
