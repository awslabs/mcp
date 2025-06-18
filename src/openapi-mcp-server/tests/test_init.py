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
"""Tests for the awslabs.openapi-mcp-server package."""

import importlib
import re
from unittest.mock import MagicMock, patch


class TestInit:
    """Tests for the __init__.py module."""

    def test_version(self):
        """Test that __version__ is defined and follows semantic versioning."""
        # Import the module
        import awslabs.openapi_mcp_server

        # Check that __version__ is defined
        assert hasattr(awslabs.openapi_mcp_server, '__version__')

        # Check that __version__ is a string
        assert isinstance(awslabs.openapi_mcp_server.__version__, str)

        # Check that __version__ follows semantic versioning (major.minor.patch)
        version_pattern = r'^\d+\.\d+\.\d+$'
        assert re.match(version_pattern, awslabs.openapi_mcp_server.__version__), (
            f"Version '{awslabs.openapi_mcp_server.__version__}' does not follow semantic versioning"
        )

    def test_module_reload(self):
        """Test that the module can be reloaded."""
        # Import the module
        import awslabs.openapi_mcp_server

        # Store the original version
        original_version = awslabs.openapi_mcp_server.__version__

        # Reload the module
        importlib.reload(awslabs.openapi_mcp_server)

        # Check that the version is still the same
        assert awslabs.openapi_mcp_server.__version__ == original_version

    def test_get_caller_info_normal_case(self):
        """Test that get_caller_info returns proper caller information in normal case."""
        # Import the function
        from awslabs.openapi_mcp_server import get_caller_info

        # Define a wrapper function to call get_caller_info
        def wrapper_function():
            return get_caller_info()

        # Call the wrapper function to get caller info
        result = wrapper_function()

        # Check that the result contains this test function's information
        assert 'test_get_caller_info_normal_case' in result
        assert 'test_init.py' in result

    @patch('inspect.currentframe')
    def test_get_caller_info_no_current_frame(self, mock_currentframe):
        """Test that get_caller_info handles the case when currentframe returns None."""
        # Import the function
        from awslabs.openapi_mcp_server import get_caller_info

        # Mock currentframe to return None
        mock_currentframe.return_value = None

        # Call get_caller_info
        result = get_caller_info()

        # Check that it returns "unknown"
        assert result == 'unknown'

    @patch('inspect.currentframe')
    def test_get_caller_info_no_parent_frame(self, mock_currentframe):
        """Test that get_caller_info handles the case when parent frame is None."""
        # Import the function
        from awslabs.openapi_mcp_server import get_caller_info

        # Create a mock frame with no parent frame
        mock_frame = MagicMock()
        mock_frame.f_back = None
        mock_currentframe.return_value = mock_frame

        # Call get_caller_info
        result = get_caller_info()

        # Check that it returns "unknown"
        assert result == 'unknown'

    @patch('inspect.currentframe')
    @patch('inspect.getframeinfo')
    def test_get_caller_info_no_caller_frame(self, mock_getframeinfo, mock_currentframe):
        """Test that get_caller_info handles the case when caller frame is None."""
        # Import the function
        from awslabs.openapi_mcp_server import get_caller_info

        # Create a mock frame hierarchy with no caller frame
        mock_caller_frame = None

        mock_parent_frame = MagicMock()
        mock_parent_frame.f_back = mock_caller_frame

        mock_frame = MagicMock()
        mock_frame.f_back = mock_parent_frame
        mock_currentframe.return_value = mock_frame

        # This test should hit the early return condition
        # without calling getframeinfo

        # Call get_caller_info
        result = get_caller_info()

        # Check that it returns "unknown"
        assert result == 'unknown'

        # Verify that getframeinfo was never called
        mock_getframeinfo.assert_not_called()
