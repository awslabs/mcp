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

"""Unit tests for AWS Security Hub MCP Server __init__.py."""

import importlib
from awslabs.security_hub_mcp_server import __version__


class TestInit:
    """Test cases for package initialization."""

    def test_version(self):
        """Test that version is defined and is a string."""
        assert __version__ is not None
        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_module_reload(self):
        """Test that the module can be reloaded without errors."""
        import awslabs.security_hub_mcp_server

        importlib.reload(awslabs.security_hub_mcp_server)
        assert awslabs.security_hub_mcp_server.__version__ is not None
