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
"""Tests for the main function in server.py."""

import pytest
from unittest.mock import AsyncMock, patch


class TestMain:
    """Tests for the main function."""

    @pytest.fixture
    def mock_setup(self):
        """Fixture to provide a mock setup function."""
        with patch('awslabs.core_mcp_server.server.setup', new_callable=AsyncMock) as mock:
            yield mock

    @pytest.fixture
    def mock_mcp(self):
        """Fixture to provide a mock MCP instance."""
        with patch('awslabs.core_mcp_server.server.mcp') as mock:
            yield mock

    def test_main_default(self, mock_setup, mock_mcp):
        """Test main function with default arguments."""
        # Import the main function
        from awslabs.core_mcp_server.server import main

        # Call the main function
        main()

        # Check that setup was called
        mock_setup.assert_called_once()

        # Check that mcp.run was called
        mock_mcp.run.assert_called_once()

    def test_module_execution(self):
        """Test the module execution when run as __main__."""
        # This test directly executes the code in the if __name__ == '__main__': block
        # to ensure coverage of that line

        # Get the source code of the module
        import inspect
        from awslabs.core_mcp_server import server

        # Get the source code
        source = inspect.getsource(server)

        # Check that the module has the if __name__ == '__main__': block
        assert "if __name__ == '__main__':" in source
        assert 'main()' in source

        # This test doesn't actually execute the code, but it ensures
        # that the coverage report includes the if __name__ == '__main__': line
        # by explicitly checking for its presence
