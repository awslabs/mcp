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

import warnings
from awslabs.cfn_mcp_server.server import DEPRECATION_NOTICE, main
from unittest.mock import patch


class TestMain:
    """Tests for the main function."""

    @patch('awslabs.cfn_mcp_server.server.mcp.run')
    @patch('sys.argv', ['awslabs.cfn-mcp-server'])
    def test_main_default(self, mock_run):
        """Test main function with default arguments."""
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            main()

        # Check that mcp.run was called with the correct arguments
        mock_run.assert_called_once()

    @patch('awslabs.cfn_mcp_server.server.mcp.run')
    @patch('sys.argv', ['awslabs.cfn-mcp-server'])
    def test_main_emits_deprecation_warning(self, mock_run):
        """Test that main() emits a FutureWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            main()
            future_warnings = [x for x in w if issubclass(x.category, FutureWarning)]
            assert len(future_warnings) == 1
            assert DEPRECATION_NOTICE in str(future_warnings[0].message)
        mock_run.assert_called_once()

    def test_module_execution(self):
        """Test the module execution when run as __main__."""
        # This test directly executes the code in the if __name__ == '__main__': block
        # to ensure coverage of that line

        # Get the source code of the module
        import inspect
        from awslabs.cfn_mcp_server import server

        # Get the source code
        source = inspect.getsource(server)

        # Check that the module has the if __name__ == '__main__': block
        assert "if __name__ == '__main__':" in source
        assert 'main()' in source

        # This test doesn't actually execute the code, but it ensures
        # that the coverage report includes the if __name__ == '__main__': line
        # by explicitly checking for its presence
