# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file.
# This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied.
# See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for the awslabs.amazon-keyspaces-mcp-server package."""

import importlib
import re


class TestInit:
    """Tests for the __init__.py module."""

    def test_version(self):
        """Test that __version__ is defined and follows semantic versioning."""
        # pylint: disable=import-outside-toplevel
        import awslabs.amazon_keyspaces_mcp_server

        assert hasattr(awslabs.amazon_keyspaces_mcp_server, '__version__')
        assert isinstance(awslabs.amazon_keyspaces_mcp_server.__version__, str)

        version_pattern = r'^\d+\.\d+\.\d+$'
        version = awslabs.amazon_keyspaces_mcp_server.__version__
        assert re.match(version_pattern, version), (
            f"Version '{version}' does not follow semantic versioning"
        )

    def test_module_reload(self):
        """Test that the module can be reloaded."""
        # pylint: disable=import-outside-toplevel
        import awslabs.amazon_keyspaces_mcp_server

        original_version = awslabs.amazon_keyspaces_mcp_server.__version__
        importlib.reload(awslabs.amazon_keyspaces_mcp_server)
        assert awslabs.amazon_keyspaces_mcp_server.__version__ == original_version
