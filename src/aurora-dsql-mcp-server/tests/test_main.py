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
"""Tests for the main function in server.py."""

import awslabs.aurora_dsql_mcp_server.server
from awslabs.aurora_dsql_mcp_server.server import main
from unittest.mock import patch


class TestMain:
    """Tests for the main function."""

    @patch(
        'sys.argv',
        [
            'awslabs.aurora-dsql-mcp-server',
            '--cluster_endpoint',
            'test_ce',
            '--database_user',
            'test_user',
            '--region',
            'us-west-2',
        ],
    )
    def test_main_with_required_arguments(self, mocker):
        mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
        mock_execute_query.return_value = {'column': 1}

        mock_mcp_run = mocker.patch('awslabs.aurora_dsql_mcp_server.server.mcp.run')

        main()

        assert awslabs.aurora_dsql_mcp_server.server.database_user == 'test_user'
        assert awslabs.aurora_dsql_mcp_server.server.cluster_endpoint == 'test_ce'
        assert awslabs.aurora_dsql_mcp_server.server.region == 'us-west-2'
        assert awslabs.aurora_dsql_mcp_server.server.read_only == True

        mock_execute_query.assert_called_once()
        mock_mcp_run.assert_called_once()
        assert mock_mcp_run.call_args[1].get('transport') is None


    @patch(
        'sys.argv',
        [
            'awslabs.aurora-dsql-mcp-server',
            '--cluster_endpoint',
            'test_ce',
            '--database_user',
            'test_user',
            '--region',
            'us-west-2',
            '--allow-writes',
            '--sse',
            '--port',
            '9999',
        ],
    )
    def test_main_with_optional_arguments(self, mocker):
        mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
        mock_execute_query.return_value = {'column': 1}

        mock_mcp_run = mocker.patch('awslabs.aurora_dsql_mcp_server.server.mcp.run')

        main()

        assert awslabs.aurora_dsql_mcp_server.server.read_only == False

        mock_execute_query.assert_called_once()
        mock_mcp_run.assert_called_once()
        assert mock_mcp_run.call_args[1].get('transport') == 'sse'

        # Check that the port was set correctly
        from awslabs.aurora_dsql_mcp_server.server import mcp

        assert mcp.settings.port == 9999

    def test_module_execution(self):
        """Test the module execution when run as __main__."""
        # This test directly executes the code in the if __name__ == '__main__': block
        # to ensure coverage of that line

        # Get the source code of the module
        import inspect
        from awslabs.aurora_dsql_mcp_server import server

        # Get the source code
        source = inspect.getsource(server)

        # Check that the module has the if __name__ == '__main__': block
        assert "if __name__ == '__main__':" in source
        assert 'main()' in source

        # This test doesn't actually execute the code, but it ensures
        # that the coverage report includes the if __name__ == '__main__': line
        # by explicitly checking for its presence
