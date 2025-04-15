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
"""Tests for the core_mcp_server package."""

import importlib
import re


class TestInit:
    """Tests for the __init__.py module."""

    def test_version(self):
        """Test that __version__ is defined and follows semantic versioning."""
        # Import the module
        import awslabs.core_mcp_server

        # Check that __version__ is defined
        assert hasattr(awslabs.core_mcp_server, '__version__')

        # Check that __version__ is a string
        assert isinstance(awslabs.core_mcp_server.__version__, str)

        # Check that __version__ follows semantic versioning (major.minor.patch)
        version_pattern = r'^\d+\.\d+\.\d+$'
        assert re.match(version_pattern, awslabs.core_mcp_server.__version__), (
            f"Version '{awslabs.core_mcp_server.__version__}' does not follow semantic versioning"
        )

    def test_module_reload(self):
        """Test that the module can be reloaded."""
        # Import the module
        import awslabs.core_mcp_server

        # Store the original version
        original_version = awslabs.core_mcp_server.__version__

        # Reload the module
        importlib.reload(awslabs.core_mcp_server)

        # Check that the version is still the same
        assert awslabs.core_mcp_server.__version__ == original_version
