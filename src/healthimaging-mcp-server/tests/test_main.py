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

"""Tests for main module."""


class TestMain:
    """Tests for main entry point."""

    def test_main_module_exists(self):
        """Test that main module can be imported."""
        import awslabs.healthimaging_mcp_server.main

        assert awslabs.healthimaging_mcp_server.main is not None

    def test_main_imports_server_main(self):
        """Test that main module imports main from server."""
        # Check that the main function is available
        from awslabs.healthimaging_mcp_server.main import main

        assert callable(main)

    def test_main_function_exists(self):
        """Test that main function exists and is callable."""
        from awslabs.healthimaging_mcp_server.main import main

        assert callable(main)

        # Verify it's the same function as in server
        from awslabs.healthimaging_mcp_server.server import main as server_main

        assert main is server_main
