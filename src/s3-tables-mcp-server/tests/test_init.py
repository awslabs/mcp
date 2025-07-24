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

"""Tests for the awslabs.s3-tables-mcp-server package."""

import importlib
import re


class TestInit:
    """Tests for the __init__.py module."""

    def test_version(self):
        """Test that __version__ is defined and follows semantic versioning."""
        # Import the module
        import awslabs.s3_tables_mcp_server

        # Check that __version__ is defined
        assert hasattr(awslabs.s3_tables_mcp_server, '__version__')

        # Check that __version__ is a string
        assert isinstance(awslabs.s3_tables_mcp_server.__version__, str)

        # Check that __version__ follows semantic versioning (major.minor.patch)
        version_pattern = r'^\d+\.\d+\.\d+$'
        assert re.match(version_pattern, awslabs.s3_tables_mcp_server.__version__), (
            f"Version '{awslabs.s3_tables_mcp_server.__version__}' does not follow semantic versioning"
        )

    def test_module_reload(self):
        """Test that the module can be reloaded."""
        # Import the module
        import awslabs.s3_tables_mcp_server

        # Store the original version
        original_version = awslabs.s3_tables_mcp_server.__version__

        # Reload the module
        importlib.reload(awslabs.s3_tables_mcp_server)

        # Check that the version is still the same
        assert awslabs.s3_tables_mcp_server.__version__ == original_version

    def test_required_modules_imported(self):
        """Test that all required modules are imported."""
        import awslabs.s3_tables_mcp_server

        # Check that required modules are available
        assert hasattr(awslabs.s3_tables_mcp_server, 'server')
        assert hasattr(awslabs.s3_tables_mcp_server, 'models')
        assert hasattr(awslabs.s3_tables_mcp_server, 'constants')

    def test_constants_defined(self):
        """Test that required constants are defined."""
        # Check that __version__ is defined and accessible
        import awslabs.s3_tables_mcp_server

        # Check that __version__ is defined
        assert hasattr(awslabs.s3_tables_mcp_server, '__version__')
