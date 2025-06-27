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
"""Tests for the awslabs.aurora-dsql-mcp-server package."""

import importlib
import re


class TestInit:
    """Tests for the __init__.py module."""

    def test_version(self):
        """Test that __version__ is defined and follows semantic versioning."""
        # Import the module
        import awslabs.aurora_dsql_mcp_server

        # Check that __version__ is defined
        assert hasattr(awslabs.aurora_dsql_mcp_server, '__version__')

        # Check that __version__ is a string
        assert isinstance(awslabs.aurora_dsql_mcp_server.__version__, str)

        # Check that __version__ follows semantic versioning (major.minor.patch)
        version_pattern = r'^\d+\.\d+\.\d+$'
        assert re.match(version_pattern, awslabs.aurora_dsql_mcp_server.__version__), (
            f"Version '{awslabs.aurora_dsql_mcp_server.__version__}' does not follow semantic versioning"
        )

    def test_module_reload(self):
        """Test that the module can be reloaded."""
        # Import the module
        import awslabs.aurora_dsql_mcp_server

        # Store the original version
        original_version = awslabs.aurora_dsql_mcp_server.__version__

        # Reload the module
        importlib.reload(awslabs.aurora_dsql_mcp_server)

        # Check that the version is still the same
        assert awslabs.aurora_dsql_mcp_server.__version__ == original_version
