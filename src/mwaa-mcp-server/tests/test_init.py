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
"""Tests for the awslabs.mwaa-mcp-server package."""

import importlib
import re


class TestInit:
    """Tests for the __init__.py module."""

    def test_version(self):
        """Test that __version__ is defined and follows semantic versioning."""
        import awslabs.mwaa_mcp_server

        assert hasattr(awslabs.mwaa_mcp_server, '__version__')
        assert isinstance(awslabs.mwaa_mcp_server.__version__, str)

        version_pattern = r'^\d+\.\d+\.\d+$'
        assert re.match(version_pattern, awslabs.mwaa_mcp_server.__version__), (
            f"Version '{awslabs.mwaa_mcp_server.__version__}' does not follow semantic versioning"
        )

    def test_mcp_server_version(self):
        """Test that MCP_SERVER_VERSION equals __version__."""
        import awslabs.mwaa_mcp_server

        assert hasattr(awslabs.mwaa_mcp_server, 'MCP_SERVER_VERSION')
        assert awslabs.mwaa_mcp_server.MCP_SERVER_VERSION == awslabs.mwaa_mcp_server.__version__

    def test_module_reload(self):
        """Test that the module can be reloaded."""
        import awslabs.mwaa_mcp_server

        original_version = awslabs.mwaa_mcp_server.__version__
        importlib.reload(awslabs.mwaa_mcp_server)
        assert awslabs.mwaa_mcp_server.__version__ == original_version
